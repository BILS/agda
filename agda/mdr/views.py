import json
import time

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from django.http import (Http404,
                         HttpResponse, StreamingHttpResponse)
from django.shortcuts import (get_object_or_404,
                              redirect,
                              render)
from django.template import RequestContext
from django.utils.text import get_text_list

from agda.forms import (CleanFulltext,
                        DynamicSearchForm,
                        FastaCleaner,
                        FormContents,
                        clean_int_range,
                        clean_kingdom,
                        clean_species_code,
                        clean_taxonomic_division,
                        clean_wildcard_like,
                        fulltext_search_help,
                        get_dynamic_search_form_data,
                        get_form,
                        get_parameter_errors,
                        range_help,
                        wildcard_like_help)
from agda.forms.cached_uploads import CachedUploadManager

from agda.settings.local import SITE_ROOT
from agda.utils import (abspath,
                        model_dict)
from agda.views import (json_response,
                        package_template_dict,
                        render_and_split,
                        script_data,
                        stream)

from jobs.views_api import api_show_results

from jobs.models import (JOB_STATUS_LEVEL_ACCEPTED,
                         JOB_STATUS_LEVEL_FINISHED,
                         get_job_or_404)

from models import (Family,
                    MDRScanJob,
                    Member,
                    mdr_package,
                    mdrlookup_tool,
                    mdrscan_tool,
                    mdrsearch_tool)
import parse_mdrscan
import scan_examples


def mdr_params(request, *args, **kw):
    return package_template_dict(request, mdr_package, *args, **kw)


def mdrscan_params(*args, **kw):
    return mdr_params(*args, tool=mdrscan_tool, **kw)


def mdrsearch_params(*args, **kw):
    return mdr_params(*args, tool=mdrsearch_tool, **kw)


def mdrlookup_params(*args, **kw):
    return mdr_params(*args, tool=mdrlookup_tool, **kw)


def top(request):
    return render(request, 'agda/package-page.html', mdr_params(request))

### Scan ###

clean_fasta = FastaCleaner(default_id='query_sequence', min_sequences=0).clean


class MDRScanForm(forms.Form):
    name = forms.CharField(max_length=100, initial='MDRScan job', help_text='Job name')
    query = forms.CharField(widget=forms.Textarea(attrs={'class': 'query-sequence'}),
                            help_text='One or more fasta format sequences',
                            required=False)
    query_file = forms.FileField(help_text='One or more fasta format sequences', label='', required=False)

    annotations = dict(
        examples=dict(query=scan_examples.adh1a_human,
                      name='MDRScan example'),
        advanced=['name'])

    _entries = None

    def clean_query(self):
        self._entries = clean_fasta(self.cleaned_data['query'])
        return self._entries

    def clean_query_file(self):
        upload = self.cleaned_data['query_file']
        if upload is False or upload is self.initial['query_file']:
            # ClearableFileInputs return False for "clear" and initial data for
            # "keep".  Any initial data is already clean, so let cached_upload
            # sort these out.
            return upload
        self._entries = clean_fasta(upload)
        return upload

    def clean(self):
        cleaned_data = super(MDRScanForm, self).clean()
        plaintext = cleaned_data.get('query')
        file = cleaned_data.get('query_file')
        if plaintext and file:
            self._errors.setdefault('query', []).append('Please give sequences in plain text or upload a file, not both.')
        if 'query' not in self._errors and 'query_file' not in self._errors and not (plaintext or file):
            self._errors.setdefault('query', []).append('At least one sequence is required.')
        return cleaned_data

    def get_query_entries(self):
        if not self.is_valid():
            raise KeyError('Cannot get entries from invalid form')
        if self._entries is not None:
            return self._entries
        return self.clean_fasta(self.initial['query_file'].open())


@transaction.atomic
def api_scan(request):
    if request.method == 'GET':
        return json_response(dict(query='Sequence(s) in fasta format.', name='A name for your job (optional)'))
    try:
        data = json.loads(request.body)
    except:
        return HttpResponse(status=400)
    try:
        entries = clean_fasta(data['query'])
    except ValidationError, e:
        return json_response(dict(complaints=str(e)), status=422)
    job = MDRScanJob(status=JOB_STATUS_LEVEL_ACCEPTED)
    job.save()
    job = MDRScanJob.objects.select_for_update().get(pk=job.id)
    job.log_create(request.agda_api_user, 'Created in api.')
    job.submit(request.agda_api_user, request.META['REMOTE_ADDR'], data.get('name'), entries)
    return redirect(api_show_results, job.slug)


@transaction.atomic
def scan(request):
    key_base = 'mdrscan.submit_job'
    cached_uploads = CachedUploadManager.get_from_session(request.session, key_base, ['query_file'])
    ok_to_accept, form = get_form(MDRScanForm, request, cached_uploads)
    if not ok_to_accept:
        cached_uploads.store_in_session()
        form_contents = FormContents(form, **form.annotations)
        return render(request, 'mdr/scan.html', mdrscan_params(request, form_contents=form_contents))
    # Job accepted
    job = MDRScanJob(status=JOB_STATUS_LEVEL_ACCEPTED)
    job.save()
    job = MDRScanJob.objects.select_for_update().get(pk=job.id)
    job.log_create(request.user, 'Created in web interface.')
    entries = form.get_query_entries()
    job.submit(request.user, request.META['REMOTE_ADDR'], form.cleaned_data['name'], entries)
    cached_uploads.clear_from_session()
    return redirect('jobs.views.show_results', job.slug)


def _scan_results_preprocess(params, results, width):
    for confidence in results:
        for query in results[confidence]:
            for family in query['families']:
                for hit in family['hits']:
                    hit['graphic_margin'] = int(float(hit['first']) / query['length'] * width)
                    hit['graphic_width'] = int(float(hit['last'] - hit['first'] + 1) / query['length'] * width)
    params['graphic_width'] = width
    params['results'] = list(sorted(results.items()))
    params['summary'] = dict(
        strong_hits=sum(len(q['families']) for q in results['strong_hits']),
        weak_hits=sum(len(q['families']) for q in results['weak_hits']),
        queries=len(results['strong_hits'])
    )


def scan_results(request, slug=None):
    job = get_job_or_404(slug=slug, select_for_update=True)
    job.update_status(request.user)
    params = mdrscan_params(request, job=job)
    if job.status == JOB_STATUS_LEVEL_FINISHED:
        width = 200
        info = json.load(open(job.resultfile('json')))
        if info['format'] == parse_mdrscan.json_format_version:
            results = info['results']
        else:
            results = parse_mdrscan.parse_mdrscan(job.resultfile('hmmpfam'), job.resultfile('query'))
        _scan_results_preprocess(params, results, width)
    elif job.is_alive:
        reload_time, interval = request.session.setdefault('mdrscan', dict()).pop(job.slug, (0, 5))
        if reload_time <= time.time():
            reload_time = max(time.time() + 5, reload_time + interval)
            interval *= 2
        request.session['mdrscan'][job.slug] = (reload_time, interval)
        request.session.modified = True
        params.update(timeout=reload_time - time.time())
        params.update(reload_time=reload_time, interval=interval)
    return render(request, 'mdr/scan-results.html', params)


### Search ###

def to_mdr_family_id(family_id):
    if family_id.isdigit():
        number = int(family_id.lstrip('0'))
    elif family_id[:3].upper() != 'MDR':
        raise ValueError
    else:
        number = int(family_id[3:].lstrip('0'))
    if not (1 <= number <= Family.objects.count()):
        raise ValueError
    return 'MDR%03d' % number


def clean_family_id(queryset, field_name, value):
    values = value.split()
    q = []
    for value in values:
        try:
            family_id = to_mdr_family_id(value)
        except:
            raise ValidationError('Ids must be on the form MDR001, or a number.')
        q.append(Q(**{field_name: family_id}))
    return queryset.filter(reduce(lambda a, b: a | b, q))


def clean_source_database(queryset, field_name, value):
    value = value.strip().lower()
    sprot = ['sp', 'sprot', 'swissprot', 'swiss-prot']
    trembl = ['tr', 'trembl']
    if value in trembl:
        value = 'tr'
    elif value in sprot:
        value = 'sp'
    else:
        raise ValidationError('Please use one of %s.' % get_text_list(sprot + trembl))
    return queryset.filter(**{field_name: value})

clean_fulltext = CleanFulltext(dict(description='description')).clean

search_parameters = (
    ('all_text', 'All text', 'Fulltext search all textual fields. ' + fulltext_search_help, clean_fulltext),
    ('description', 'Description', 'Fulltext search sequence descriptions. ' + fulltext_search_help, clean_fulltext),
    ('family_id', 'Family ID', 'One or more MDR family ids.', clean_family_id),
    ('family_name', 'Family name', 'One or more MDR family names. ' + wildcard_like_help),
    ('source_database', 'Source database', 'Sequence origin; trembl or swissprot.', clean_source_database),
    ('uniprot_ac', 'Uniprot AC', 'One or more UniProtKB accession numbers. ' + wildcard_like_help),
    ('uniprot_id', 'Uniprot ID', 'One or more UniProtKB ids. ' + wildcard_like_help),
    ('species', 'Species', 'One or more species latin name. ' + wildcard_like_help),
    ('species_common_name', 'Species common name', 'One or more species common name. ' + wildcard_like_help),
    ('species_code', 'Species code', 'One or more Uniprot species codes, e.g: HUMAN, GADMO or 9RHOB.', clean_species_code),
    ('taxonomic_division', 'Taxonomic division', 'One or more NCBI Taxonomy division codes or names, e.g: viruses, mammals, pln, or pri.', clean_taxonomic_division),
    ('kingdom', 'Kingdom', 'One or more kingdom letter, e.g: A, B, E or V', clean_kingdom),
    ('sequence_length', 'Sequence length', range_help, clean_int_range),
)


def get_families(member_dicts):
    families = dict()
    for member in member_dicts:
        family = families.get(member['family_id'])
        if not family:
            family = model_dict(Family.objects.get(pk=member['family_id']))
            families[member['family_id']] = family
            family['members'] = []
        member['source_database'] = 'Swiss-Prot' if member['source_database'] == 'sp' else 'TrEMBL'
        member['length'] = member['stop'] - member['start'] + 1
        family['members'].append(member)
    return families


def api_search(request):
    if request.method == 'GET':
        return json_response({'parameter': 'value', 'parameter...': 'value...'})
    try:
        query = json.loads(request.body)
    except:
        return HttpResponse(status=400)
    form = DynamicSearchForm(search_parameters, Member, get_dynamic_search_form_data(query), default_cleaner=clean_wildcard_like)
    if not form.is_valid():
        return json_response(dict(complaints=get_parameter_errors(form)), status=422)
    families = get_families(form.cleaned_data['queryset'].values().iterator())
    return json_response(families)


def render_search_hits(families):
    member_template = open(abspath(SITE_ROOT, 'mdr/templates/mdr/search-member-simple.html')).read()
    for name, family in sorted(families.iteritems()):
        pre, post = render_and_split('mdr/search-family.html', ['members'], dict(family=family))
        yield pre
        for member in family['members']:
            member['family_size'] = family['size']
            member['length'] = member['stop'] - member['start'] + 1
            yield member_template % member
        yield post


def search_results(request, member_dicts):
    pre, post = render_and_split('mdr/search-results.html', ['hits'], mdrsearch_params(request), RequestContext(request))
    families = get_families(member_dicts)
    return HttpResponse(stream(pre, render_search_hits(families), post))


def search(request):
    if request.POST:
        form = DynamicSearchForm(search_parameters, Member, request.POST, default_cleaner=clean_wildcard_like)
        if form.is_valid():
            members = form.cleaned_data['queryset'].values().iterator()
            return search_results(request, members)
    else:
        form = DynamicSearchForm(search_parameters, Member)  # An unbound form
    params = mdrsearch_params(request,
                              form=form,
                              criteria=form.criteria_field_pairs(),
                              parameter_help=script_data(dict((t[0], t[2]) for t in search_parameters)))
    return render(request, 'mdr/search.html', params)


### Lookup ###

class LookupForm(forms.Form):
    family_id = forms.CharField(help_text="MDR family ID, on the form MDR001.")


def api_family_lookup(request):
    family_id = None
    if request.method == 'GET':
        return json_response(dict(id="MDR family ID, e.g: MDR085"))
    try:
        family_id = to_mdr_family_id(json.loads(request.body)['id'])
    except:
        raise Http404('no such family')
    family = model_dict(get_object_or_404(Family, id=family_id))
    family['members'] = list(Member.objects.filter(family_id=family_id).values().iterator())
    return json_response(family)


def family_lookup(request, family_id=''):
    if not family_id:
        family_id = request.GET.get('family_id', '')
        if family_id:
            return redirect(family_lookup, family_id)
    if not family_id:
        return render(request, 'mdr/lookup.html', mdrlookup_params(request, form=LookupForm()))
    original_id = family_id
    try:
        family_id = to_mdr_family_id(family_id)
    except:
        raise Http404('no such family')
    if original_id != family_id:
        return redirect(family_lookup, family_id)
    members = Member.objects.filter(family_id=family_id).values().iterator()
    families = get_families(members)

    pre, post = render_and_split('mdr/lookup-results.html', ['hits'], mdrlookup_params(request), RequestContext(request))
    return StreamingHttpResponse(stream(pre, render_search_hits(families), post))
