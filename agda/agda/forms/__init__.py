import shlex
import string

from django import forms
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Q
from django.utils.html import mark_safe
from django.utils.text import get_text_list

from core import fasta


def get_form_with_cached_uploads(form_class, request, cached_uploads, **extra):
    """As get_form, with cached_uploads."""
    extra.setdefault('initial', dict()).update(cached_uploads)
    if request.method == 'POST':  # Return filled-in form
        form = form_class(request.POST, request.FILES, **extra)
        cached_uploads.manage_inputs(request, form)
        return form.is_valid(), form
    return False, form_class(**extra)  # Present empty form


def get_form(form_class, request, cached_uploads=None, **extra):
    """
    Instantiate a form and check if it is filled-out and valid.

    Returns (bool, form) where the former is True only if the form is
    filled-out and .is_valid().

    Also manages ClearableFileInputs so that they work as advertised for all
    given cached uploads (cached_uploads.CachedUploads).

    This is a simple helper for untangling the often prosaic but convoluted
    code paths of standard Django form handling boilerplate code.
    """
    if cached_uploads is not None:
        return get_form_with_cached_uploads(
            form_class,
            request,
            cached_uploads
        )
    if request.method == 'POST':  # Return filled-in form
        form = form_class(request.POST, request.FILES, **extra)
        return form.is_valid(), form
    return False, form_class(**extra)  # Present empty form


def change_message_from_form(form, log_value_fields=[]):
    """Return a description of fields changed in the form."""
    if not form.changed_data:
        return "Changed no fields."
    else:
        res = []
        changed_fields = form.changed_data[:]
        # Handle fields were we will show the new value:
        for vf in log_value_fields:
            if vf in changed_fields:
                res.append("Changed %s to '%s'." % (vf, form.cleaned_data[vf]))
                changed_fields.remove(vf)

        # Handle the rest of the fields
        if changed_fields:
            res.append("Changed %s." % (get_text_list(changed_fields, "and")))

        return " ".join(res)


class FormContents(list):
    """
    A list of things that can go into a form, with benefits.

    This class wraps up fields and associated information in a manner easily
    accessible from within templates.

    Each item in the list is a dict whose key 'type' indicates what other items
    are present.

    | type 'field' has these items:
    | field: a django.forms.BoundField
    | example: an example value
    | help_url: a url to user friendly parameter documentation.
    | comment: text that should be displayed next to the field (field.help_text being more of a tooltip)

    | type 'heading' has these items:
    | tag: name of the heading tag to use
    | text: the heading text.

    | type 'text' has these items:
    | text: the text to display.
    """
    example_and_reset_info = mark_safe('You can <a onclick="resetValues(this, \'example\')" title="Insert example values" href="javascript:void(0);">use some example data</a>, or <a title="Insert example values" href="javascript:void(0);" onclick="resetValues(this)">reset the form</a> to default values.')  # noqa

    def __init__(self, form, intro=None, advanced=[], examples={},
                 comments={}, help_urls={}, extra={}, reset={}):
        def field_item(field):
            initial = form.initial.get(field.name, field.field.initial)
            if initial is None:
                initial = ''
            return dict(
                type='field',
                field=field,
                advanced=field.name in advanced,
                example=examples.get(field.name, ''),
                initial=initial,
                comment=comments.get(field.name, ''),
                help_url=help_urls.get(field.name, ''),
                reset=reset.get(field.name, not isinstance(field.field, forms.FileField) and field.name in examples))
        super(FormContents, self).__init__(field_item(field) for field in form)
        self.insert_non_field_errors(0)
        self.intro = intro
        self.form = form
        if isinstance(extra, dict):
            extra = extra.items()
        for name, items in extra:
            if not isinstance(items, (list, tuple)):
                items = [items]
            i = self.index(name)
            self[i:i] = items
        if not self.has_item(type='form_buttons'):
            self.insert_form_buttons(len(self))
        if advanced and not self.has_item(type='advanced_field_display_toggle'):
            i = self.find(advanced=True)
            self.insert_advanced_field_display_toggle(i)
            self.insert_form_buttons(i)
            if self[-1]['type'] == 'form_buttons':
                self[-1]['advanced'] = True

    def index(self, key):
        if isinstance(key, basestring):
            for i, value in enumerate(self):
                if getattr(value.get('field'), 'name', None) == key:
                    return i
            raise KeyError('no such field')
        return super(FormContents, self).index(key)

    def find(self, **kw):
        for i, item in enumerate(self):
            for k, v in kw.items():
                if item.get(k) == v:
                    return i
        return -1

    def has_item(self, **kw):
        return self.find(**kw) >= 0

    def insert(self, key, item):
        if isinstance(key, basestring):
            key = self.index(key)
        super(FormContents, self).insert(key, item)

    def insert_non_field_errors(self, key):
        """Placeholder for any non-field error messages."""
        self.insert(key, dict(type='non_field_errors'))

    def insert_advanced_field_display_toggle(self, key):
        """Link to show/hide advanced properties."""
        self.insert(key, dict(type='advanced_field_display_toggle'))

    def insert_form_buttons(self, key, advanced=False):
        """Form submit and (optionally) also reset buttons."""
        self.insert(key, dict(type='form_buttons', advanced=advanced))

    def insert_extra(self, key, type, **kw):
        self.insert(key, dict(type=type, **kw))

    def insert_heading(self, key, text, tag='h3'):
        """Insert a heading item just before key."""
        self.insert_extra(key, type='heading', tag=tag, text=text)

    def insert_text(self, key, text):
        """Insert a text item just before key."""
        self.insert_extra(key, type='text', text=text)


# Dynamic search form #

class Parameter(object):
    def __init__(self, name, nickname, help=None, cleaner=None):
        self.name = name
        self.nickname = nickname
        self.cleaner = cleaner
        self.help = help


class DynamicSearchForm(forms.Form):
    parameter_template = 'parameter_%s'
    value_template = 'value_%s'

    def __init__(self, parameters, model, *args, **kw):
        num_criteria = kw.pop('num_criteria', None)
        if not num_criteria:
            data = kw.get('data', (args and args[0]) or {})
            num_criteria = self.get_num_criteria(data) or 4
        self.num_criteria = num_criteria
        self.model = model
        self.parameters = []
        for p in parameters:
            if isinstance(p, (list, tuple)):
                p = Parameter(*p)
            self.parameters.append(p)
        parameter_field = kw.pop('parameter_field', forms.ChoiceField)
        self.default_cleaner = kw.pop('default_cleaner', lambda qs, p, v: qs.filter(**{p: v}))
        value_field = kw.pop('value_field', lambda: forms.Field(required=False))
        super(DynamicSearchForm, self).__init__(*args, **kw)
        for i in range(self.num_criteria):
            self.fields[self.par(i)] = parameter_field((p.name, p.nickname) for p in self.parameters)
            self.fields[self.val(i)] = value_field()

    @classmethod
    def get_num_criteria(cls, data):
        """Determine the number of search criteria used in the given data.

        Requires all
        """
        i = 0
        while data.get(cls.par(i)) is not None and data.get(cls.val(i)) is not None:
            i += 1
        return i

    @classmethod
    def par(self, i):
        return self.parameter_template % i

    @classmethod
    def val(self, i):
        return self.value_template % i

    def criteria_field_pairs(self):
        return [(self[self.par(i)], self[self.val(i)]) for i in range(self.num_criteria)]

    def is_blank(self):
        for i in self.num_criteria:
            if not self.cleaned_data[self.val(i)].isspace():
                return False
        return True

    def clean(self):
        super(DynamicSearchForm, self).clean()
        qs = self.model.objects
        cleaners = dict((p.name, p.cleaner) for p in self.parameters if p.cleaner)
        for i in range(self.num_criteria):
            p = self.cleaned_data[self.par(i)]
            v = self.cleaned_data.get(self.val(i))
            if not v:
                # Criteria with empty value are ignored.
                continue
            try:
                # Get and call cleaner with (queryset, field_name, value)
                qs = cleaners.get(p, self.default_cleaner)(qs, p, v)
            except ValidationError, e:
                self._errors[self.val(i)] = self.error_class(e.messages)
                del self.cleaned_data[self.val(i)]
                del self.cleaned_data[self.par(i)]
        self.cleaned_data['queryset'] = qs
        return self.cleaned_data


# json api conversion helpers #

def get_dynamic_search_form_data(query):
    """Create form parameter_0:value_0 data dict.

    Query can be a dict or any other parameter:val iterable. For example be a
    dict from a json body in a restful api request.
    """
    data = {}
    if isinstance(query, dict):
        query = query.items()
    for i, (parameter, value) in enumerate(query):
        data[DynamicSearchForm.par(i)] = parameter
        data[DynamicSearchForm.val(i)] = value
    return data


def get_parameter_errors(form):
    """
    Create a parameter_name:error_list dict from form parameter_0:value_0
    errors.

    Good for making helpful api error response bodies.
    """
    errors = dict()
    for name, messages in form._errors.items():
        if name == '__all__':
            errors['all'] = messages
        elif name.startswith('value_') or name.startswith('parameter_'):
            number = int(name.rsplit('_', 1)[1])
            name = form.data[form.par(number)]
            errors.setdefault(name, []).extend(messages)
    return errors


# DynamicSearchForm cleaners #

class CleanIntRange(object):
    type = int
    type_error_msg = 'Ensure boundaries are whole numbers.'

    def clean(self, queryset, field_name, value):
        words = [v.strip() for v in value.split(':')]
        if len(words) == 0:
            return
        if len(words) > 2:
            raise ValidationError('Ensure this value has at most one colon character (it has %(show_value)s).', 'max_colons', dict(show_value=len(words) - 1))
        if len(words) == 1:
            length = self.clean_boundary(words[0])
            return queryset.filter(**{field_name: length})
        lower = self.clean_boundary(words[0])
        upper = self.clean_boundary(words[1])
        if lower is None and upper is None:
            raise ValidationError('Ensure that at least one of lower and upper boundary is set (neither is currently set).', 'no_bounds')
        if lower is not None:
            queryset = queryset.filter(**{field_name + '__gte': lower})
        if upper is not None:
            queryset = queryset.filter(**{field_name + '__lte': upper})
        return queryset

    def clean_boundary(self, literal):
        try:
            if literal:
                return self.type(literal)
        except:
            raise ValidationError(self.type_error_msg, 'boundary_type')


class CleanFloatRange(CleanIntRange):
    type = float
    type_error_msg = 'Ensure boundaries are decimal numbers.'

clean_int_range = CleanIntRange().clean
clean_float_range = CleanFloatRange().clean

range_help = ('Give lower:upper bounds; omit either to leave unbounded in that direction.')


class CleanFulltext(object):
    def __init__(self, index={}):
        """index is a fieldname:index_name dict. Any fields not specified here
        will be matched against the 'default' index.
        """
        self.index = index

    def clean(self, queryset, field_name, value):
        return queryset.search(value.strip(), index=self.index.get(field_name, 'default'))

clean_fulltext = CleanFulltext().clean
fulltext_search_help = (
    'Prefix + or - to a word to require its presence or absence. '
    'Enclose a phrase in double quotes " to search for an exact phrase. '
    'Wildcards * can be suffixed match everything that starts with the word.'
    )


def clean_like(self, queryset, field_name, value):
    q = []
    for term in shlex.split(str(value)):
        q.append(Q(**{field_name + '__icontains': term}))
    if not q:
        return
    return queryset.filter(reduce(lambda a, b: a | b, q))


def clean_wildcard_like(queryset, field_name, value):
    meta = queryset.model._meta
    _qn = connection.ops.quote_name
    column = (f.column for f in meta.fields if f.name == field_name).next()
    templ = '%s.%s LIKE %%s' % (_qn(meta.db_table), _qn(column))
    params = []
    for term in shlex.split(str(value)):
        params.append('%' + term.replace('*', '%').strip('%') + '%')
    where = [' OR '.join([templ] * len(params))]
    return queryset.extra(where=where, params=params)

wildcard_like_help = ('Use wildcards * to match zero or more characters.')


def clean_species_code(queryset, field_name, value):
    codes = value.upper().split()
    q = []
    for code in codes:
        if len(code) > 5:
            raise ValidationError('Give one or more Uniprot species codes, e.g: HUMAN, 9TURD or RAT.')
        q.append(Q(uniprot_id__endswith=code))
    return queryset.filter(reduce(lambda a, b: a | b, q))

division_codes = {'Unassigned': 'Una',
                  'Environmental samples': 'Env',
                  'Synthetic': 'Syn',
                  'Phages': 'Phg',
                  'Viruses': 'Vrl',
                  'Bacteria': 'Bct',
                  'Plants': 'Pln',
                  'Invertebrates': 'Inv',
                  'Vertebrates': 'Vrt',
                  'Mammals': 'Mam',
                  'Rodents': 'Rod',
                  'Primates': 'Pri'}


def clean_taxonomic_division(queryset, field_name, value):
    divisions = value.split()
    q = []
    for div in divisions:
        div = div.capitalize()
        if div not in division_codes.values():
            for name, code in division_codes.items():
                if name.startswith(div):
                    div = code
        if div not in division_codes.values():
            raise ValidationError('Give one or more NCBI Taxonomy division names or codes, e.g: viruses, mammals, pln, or pri.')
        q.append(Q(**{field_name: div}))
    return queryset.filter(reduce(lambda a, b: a | b, q))


def clean_kingdom(queryset, field_name, value):
    kingdoms = ''.join(value.upper().split())
    q = []
    for kingdom in kingdoms:
        if kingdom not in 'ABEV':
            raise ValidationError('Give one or more kingdom characters, e.g: A, B, E or V.')
        q.append(Q(kingdom=kingdom))
    return queryset.filter(reduce(lambda a, b: a | b, q))


# General cleaners #

class FastaCleaner(object):
    chars = string.letters
    id_chars = (string.letters + string.digits +
                '|'  # commonly used db|ac|id separator.
                '_'  # commonly used in uniprot ITM2A_HUMAN ids.
                '-'  # common sliceoform P765V62-1 indicator
                '.'  # common sequence version indicator P765V62.3
                '/'  # common sequence range indicator ITM2A_HUMAN/32-57
                )
    description_chars = (string.letters + string.digits +
                         string.punctuation.replace('`', '').replace('$', '') +
                         " \t"  # Whitespace.
                         "\x01"  # Header separator.
                         )

    def __init__(self,
                 chars=None,
                 id_chars=None,
                 description_chars=None,
                 unique_ids=True,
                 default_id=None,
                 min_length=1,
                 max_length=None,
                 min_sequences=1,
                 max_sequences=None):
        self.chars = set(chars or self.chars)
        self.id_chars = set(id_chars or self.id_chars)
        self.description_chars = set(chars or self.description_chars)
        self.unique_ids = unique_ids
        self.default_id = default_id
        self.min_length = min_length
        self.max_length = max_length
        self.min_sequences = min_sequences
        self.max_sequences = max_sequences

    def clean(self, plaintext):
        try:
            plaintext = str(plaintext)
        except UnicodeError, e:
            raise ValidationError('Sequence seems to contain illegal characters.')
        try:
            try:
                entries = fasta.entries(plaintext)
            except fasta.FormatError:
                if not self.default_id:
                    raise
                entries = fasta.entries((">%s\n" % self.default_id) + plaintext)
        except fasta.FastaError, e:
            raise ValidationError(e.message)

        plural = lambda num: 's' if num > 1 else ''
        if len(entries) < self.min_sequences:
            raise ValidationError('Requires at least %s sequence%s.' % (self.min_length, plural(self.min_sequences)))
        if self.max_sequences is not None and len(entries) > self.max_sequences:
            raise ValidationError('Allows at most %s sequence%s.' % (self.min_length, plural(self.max_sequences)))
        ids = set([])
        for i, entry in enumerate(entries):
            alias = str(i + 1) + ' ' + entry.id
            if len(entry) < self.min_length:
                raise ValidationError('Sequence %s is shorter than the required length %s.' % (alias, self.min_length))
            if self.max_length and len(entry) > self.max_length:
                raise ValidationError('Sequence %s is longer than the allowed length %s.' % (alias, self.max_length))
            if self.unique_ids:
                if entry.id in ids:
                    raise ValidationError('Id of sequence %s is not unique.' % alias)
                ids.add(entry.id)
            illegal_chars = get_text_list(["'%s'" % ch for ch in set(entry.sequence) - self.chars], 'and')
            if illegal_chars:
                raise ValidationError("Sequence%s has illegal characters %s." % (alias, illegal_chars))
            illegal_id_chars = get_text_list(["'%s'" % ch for ch in set(entry.id) - self.id_chars], 'and')
            if illegal_id_chars:
                raise ValidationError("Id of sequence %s has illegal characters %s." % (alias, illegal_id_chars))
            illegal_description_chars = get_text_list(["'%s'" % ch for ch in set(entry.description) - self.description_chars], 'and')
            if illegal_description_chars:
                raise ValidationError("Description of sequence %s has illegal characters %s." % (alias, illegal_description_chars))

        return entries
