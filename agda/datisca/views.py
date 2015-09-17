import json
import os
import time

from django import forms
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils.text import get_text_list
from django.db import transaction

from agda.forms import FastaCleaner, FormContents, get_form
from agda.forms.cached_uploads import CachedUploadManager
from agda.views import (json_response,
                        package_template_dict,)

from jobs.views_api import api_show_results

from jobs.models import (JOB_STATUS_LEVEL_ACCEPTED,
                         JOB_STATUS_LEVEL_DELETED,
                         JOB_STATUS_LEVEL_FINISHED,
                         get_job_or_404)

import examples
from models import (DatiscaNoduleBlastJob,
                    datisca_package,
                    datisca_nodule_blast_tool)
import parse_blast


def datisca_params(request, *args, **kw):
    return package_template_dict(request, datisca_package, *args, **kw)


def nodule_blast_params(request, *args, **kw):
    return datisca_params(request, *args, tool=datisca_nodule_blast_tool, **kw)


def top(request):
    return render(request, 'datisca/top.html', datisca_params(request))

api_clean_fasta = FastaCleaner(default_id='query_sequence').clean

### nodule_trans_blast ###

blast_program_choices = (
    ('blastn', 'blastn - Nucleotide query, nucleotide db'),
    ('tblastn', 'tblastn - Protein query, translated db'),
    ('tblastx', 'tblastx - Translated query, translated db'),
    )

db_choices = (
    ('reads', '454 sequencing reads'),
    ('contigs', 'Contigs'),
    ('assembly', 'Trinity_assembly'),
    ('all', 'All'),
    )

dbdir = os.path.join(settings.DATA_ROOT, 'pub', 'datisca', '2012.1')
db_files = dict(reads=os.path.join(dbdir, 'data_454_sequence_tp.fa'),
                contigs=os.path.join(dbdir, 'trinity_plus_454.fa.cap.contigs.fa'),
                assembly=os.path.join(dbdir, 'trinity_assembly.fa'),
                all=os.path.join(dbdir, 'all'))


class NoduleTransForm(forms.Form):
    program = forms.ChoiceField(blast_program_choices, label='Program', initial='blastn', help_text="Blast algorithm.")
    db = forms.ChoiceField(db_choices, label='Database', initial='contigs', help_text="Sequence database to search.")
    evalue = forms.FloatField(label='E-value', initial='10', help_text="Search tolerance.")
    query = forms.CharField(widget=forms.Textarea(attrs={'class': 'query-sequence'}),
                            help_text='One or more fasta format sequences',
                            required=False)
    query_file = forms.FileField(help_text='One or more fasta format sequences', label='', required=False)
    name = forms.CharField(max_length=100, initial='NoduleBlast job', help_text='Job name')

    annotations = dict(
        examples=dict(query=examples.contig1_partial,
                      program='blastn',
                      db='contigs',
                      evalue=10,
                      name='NoduleBlast example'),
        advanced=['name'])

    clean_fasta = FastaCleaner(default_id='query_sequence', min_sequences=0).clean
    _entries = None

    def clean_db(self):
        return db_files[self.cleaned_data['db']]

    def clean_query(self):
        self._entries = self.clean_fasta(self.cleaned_data['query'])
        return self._entries

    def clean_query_file(self):
        upload = self.cleaned_data['query_file']
        if upload is False or upload is self.initial['query_file']:
            # ClearableFileInputs return False for "clear" and initial data for
            # "keep".  Any initial data is already clean, so let cached_upload
            # sort these out.
            return upload
        self._entries = self.clean_fasta(upload)
        upload.seek(0)
        return upload

    def clean(self):
        cleaned_data = super(NoduleTransForm, self).clean()
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


def api_nodule_trans_blast(request):
    program_names = [choice[0] for choice in blast_program_choices]
    db_names = [choice[0] for choice in db_choices]
    if request.method == 'GET':
        help = dict(query='Nucleotide sequence(s) in fasta format.',
                    db=get_text_list(db_names),
                    program=get_text_list(program_names),
                    evalue='10',
                    name='A name for your job.')
        return json_response(help)
    try:
        data = dict(json.loads(request.body))
    except:
        return HttpResponse(status=400)
    form = NoduleTransForm(data, initial=dict(query_file=None))
    if not form.is_valid():
        return json_response(dict(complaints=form._errors), status=422)
    job = DatiscaNoduleBlastJob(status=JOB_STATUS_LEVEL_ACCEPTED)
    job.save()
    job.log_create(request.agda_api_user, 'Created in api.')
    job.submit(request.agda_api_user,
               request.META['REMOTE_ADDR'],
               form.cleaned_data['name'],
               form.cleaned_data['program'],
               form.get_query_entries(),
               form.cleaned_data['db'],
               form.cleaned_data['evalue'])
    return redirect(api_show_results, job.slug)


@transaction.atomic
def nodule_trans_blast(request):
    key_base = 'datisca.nodule_trans_blast.submit_job'
    cached_uploads = CachedUploadManager.get_from_session(request.session, key_base, ['query_file'])
    ok_to_accept, form = get_form(NoduleTransForm, request, cached_uploads)
    if not ok_to_accept:
        cached_uploads.store_in_session()
        form_contents = FormContents(form, **form.annotations)
        return render(request, 'datisca/nodule_trans_blast.html', nodule_blast_params(request, form_contents=form_contents))
    # Job accepted
    job = DatiscaNoduleBlastJob(status=JOB_STATUS_LEVEL_ACCEPTED)
    job.save()
    job = DatiscaNoduleBlastJob.objects.select_for_update().get(pk=job.id)
    job.log_create(request.user, 'Created in web interface.')
    job.submit(request.user,
               request.META['REMOTE_ADDR'],
               form.cleaned_data['name'],
               form.cleaned_data['program'],
               form.get_query_entries(),
               form.cleaned_data['db'],
               form.cleaned_data['evalue'])
    cached_uploads.clear_from_session()
    return redirect('jobs.views.show_results', job.slug)


def preprocess_nodule_blast(params):
    graphic_size = 200
    params['graphic_width'] = graphic_size
    for query in params['results']['queries']:
        query_length = float(query['length'])
        scale_factor = graphic_size / query_length
        for hit in query['hits']:
            for region in hit['regions']:
                region['graphic_start'] = region['start'] * scale_factor
                region['graphic_width'] = region['length'] * scale_factor


@transaction.atomic
def nodule_trans_blast_results(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    job.update_status(request.user)
    if job.status == JOB_STATUS_LEVEL_DELETED:
        raise Http404('no such job')
    params = nodule_blast_params(request, job=job)
    if job.status == JOB_STATUS_LEVEL_FINISHED:
        data = json.load(open(job.resultfile('json')))
        results = data['results']
        if data['format'] != parse_blast.json_format_version:
            result_fh = open(job.resultfile('blast'))
            query_fh = open(job.resultfile('query'))
            results = parse_blast.parse_blast(result_fh, query_fh)
        params['results'] = results
        preprocess_nodule_blast(params)
    elif job.is_alive:
        reload_time, interval = request.session.setdefault('datisca_nodule_trans_blast', dict()).pop(job.slug, (0, 5))
        if reload_time <= time.time():
            reload_time = max(time.time() + 5, reload_time + interval)
            interval *= 2
        request.session['datisca_nodule_trans_blast'][job.slug] = (reload_time, interval)
        request.session.modified = True
        params.update(timeout=reload_time - time.time())
        params.update(reload_time=reload_time, interval=interval)
    return render(request, 'datisca/nodule_trans_blast_results.html', params)
