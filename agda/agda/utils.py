# -*- coding: utf-8 -*-
import os
import re
from unicodedata import decomposition

from django.conf import settings
from django.utils.text import get_text_list


def getattrs(obj, attr_names=[], alias={}):
    """Get attribute values as a dict.

    obj can be any object.
    attr_names should be attribute names.
    alias is an attr_name:alias dict of attributes that should be renamed.

    Good for pulling of initial form data out of models objects.
    """
    return dict((alias.get(attr, attr), getattr(obj, attr)) for attr in attr_names)


def model_dict(model_obj, fields=None, exclude=[], alias={}):
    """Return a field_name:value dict for a model object.

    fields should be a list of field names, or None for all.
    exclude should be a list of field names to exclude.
    """
    if fields is None:
        fields = [f.name for f in model_obj._meta.fields]
    fields = [name for name in fields if name not in exclude]
    return getattrs(model_obj, fields, alias)


def get_initial(obj, form):
    """Dict of initial data for form using obj attrs with same names."""
    return getattrs(obj, form.fields)

u2a = {u'æ': u'ae',
       u'Æ': u'AE',
       u'ø': u'o',
       u'Ø': u'O',
       u'ß': u'ss',
       u'þ': u'th',
       u'ð': u'd',
       u'´': u"'"}


def asciify(string):
    '''"ASCIIfy" a Unicode string by stripping all umlauts, tildes, etc.'''
    temp = u''
    for char in string:
        # Special case a few characters that don't decompose
        if char in u2a:
            temp += u2a[char]
            continue

        decomp = decomposition(char)
        if decomp:  # This character had a decomposition
            temp += unichr(int(decomp.split()[0], 16))
        else:  # No decomposition available
            temp += char
    return temp

### DB stuff.


def rows(cursor):
    row = cursor.fetchone()
    while row:
        yield row
        row = cursor.fetchone()


def get_columns(model, fields):
    columns = []
    for field in fields:
        if isinstance(field, str):
            field = model._meta.get_field(field, many_to_many=False)
        columns.append(field.column)
    return columns


### Files ###

def abspath(origin, *relpath):
    """Return the absolute path to the path specified relative to origin.

    If origin is a path to a file, relpath is interpreted as relative to the
    containing directory.
    """
    if os.path.isfile(origin):
        origin = os.path.dirname(origin)
    return os.path.join(origin, *relpath)


### Change message.

#
# ModelDiffer
#
# Find out and report on changed fields, for example to send an email
# about what has been edited. Usage example:
#
# md = ModelDiffer(contact)
# ... do some changes to contact ...
# contact.save()
# md.update(contact)
# ... include md.get_change_report() in an email


class ModelDiffer(object):
    def __init__(self, obj):
        self.model = obj.__class__
        self.fields = []
        self.field_to_verbose = {}
        for f in self.model._meta.fields:
            self.fields.append(f.name)
            self.field_to_verbose[f.name] = f.verbose_name
        self.pk = obj.pk
        self.old_values = dict((f, getattr(obj, str(f))) for f in self.fields)

    def update(self, obj):
        self.new_values = dict((f, getattr(obj, str(f))) for f in self.fields)

    def get_changed_fields(self):
        changed = []
        for f in self.fields:
            if self.new_values[f] != self.old_values[f]:
                changed.append(dict(field=f,
                                    verbose_name=self.field_to_verbose[f],
                                    old_value=self.old_values[f],
                                    new_value=self.new_values[f]))
        return changed

    def get_changed_field_names(self):
        changed = []
        for f in self.fields:
            if self.new_values[f] != self.old_values[f]:
                changed.append(f)
        return changed

    def get_changed_fields_text_list(self):
        changed = self.get_changed_field_names()
        if not changed:
            return "no fields"
        else:
            return get_text_list(changed, "and")

    def get_unchanged_fields(self):
        unchanged = []
        for f in self.fields:
            if self.new_values[f] == self.old_values[f]:
                unchanged.append(dict(field=f,
                                      verbose_name=self.field_to_verbose[f],
                                      value=self.old_values[f]))
        return unchanged

    def get_change_report(self):
        def fix_multiline(s, indent):
            s = unicode(s)
            newline = "\n" + (" " * indent)
            return re.sub(r'\n', newline, s.rstrip())

        lines = []
        changed = self.get_changed_fields()

        if changed:
            lines.append("Changed fields")
            lines.append("")
            for f in changed:
                old = fix_multiline(f["old_value"], indent=22)
                new = fix_multiline(f["new_value"], indent=22)
                lines.append("%20s: %s" % (f["verbose_name"].capitalize(), old))
                lines.append("%17s --> %s" % ("", new))
                lines.append("")

        else:
            lines.append("No fields changed.")

        return "\n".join(lines) + "\n"

    def get_change_message(self, valueless=[]):
        changed = self.get_changed_field_names()
        out = ["Changed %s to '%s'." % (name, unicode(self.new_values[name])) for name in changed if name not in valueless]
        if valueless:
            tmp = [name for name in valueless if name in changed]
            out.append('Changed %s.' % get_text_list(tmp, 'and'))
        return ' '.join(out)
