import os
import simplejson
import time

from django import forms
from django.shortcuts import (Http404,
                              HttpResponse,
                              redirect,
                              render)
from django.db import transaction
from django.contrib.auth.decorators import permission_required

from agda.forms.cached_uploads import (CachedUploadManager)
from agda.forms import (FormContents,
                        get_form)
from jobs.models import (JOB_STATUS_LEVEL_ACCEPTED,
                         JOB_STATUS_LEVEL_DELETED,
                         JOB_STATUS_LEVEL_FINISHED,
                         get_job_or_404)
from agda.views import json_response, package_template_dict

from jobs.views_api import api_show_results

import examples
from models import (PredictallJob,
                    clean_fasta,
                    pconsc_package,
                    predictall_tool)

# I expect these will be parameterized before long.
scheduler = 'slurm'
#hhblitsdb = '/srv/agda/db/hhsuite/uniprot20/2012_10/uniprot20_2012_10_klust20_dc_2012_12_10.tar.gz'
#jackhmmerdb = '/srv/agda/db/uniprot/2013_06/uniref90.fasta.gz'
hhblitsdb = '/srv/agda/db/hhsuite/uniprot20/2013_03/uniprot20_2013_03.tar.gz'
jackhmmerdb = '/srv/agda/db/uniprot/2014_04/uniref90.fasta.gz'


def pconsc_params(request, *args, **kw):
    return package_template_dict(request, pconsc_package, *args, **kw)


def predictall_params(request, *args, **kw):
    return pconsc_params(request, *args, tool=predictall_tool, **kw)


@permission_required("pconsc.access_predictalljob")
def top(request):
    return render(request, 'pconsc/top.html', pconsc_params(request))


class PredictallForm(forms.Form):
    query = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'class': 'fixed-width'}),
                            help_text='One fasta format sequence.',
                            required=False)
    query_file = forms.FileField(help_text='Alternatively, upload the sequence from a file.', label='', required=False)
    name = forms.CharField(max_length=100, initial='PredictAll job', help_text='Job name')

    annotations = dict(
        examples=dict(query=examples.example1, name='PredictAll example'),
        advanced=['name']
    )

    _entries = None

    def clean_query(self):
        self._entries = clean_fasta(self.cleaned_data['query'])
        return self._entries

    def clean_query_file(self):
        upload = self.cleaned_data['query_file']
        if upload is False or upload is self.initial['query_file']:
            # ClearableFileInputs return False for "clear" and initial data
            # for "keep".  Any initial data is already clean, so let
            # cached_upload sort these out.
            return upload
        self._entries = clean_fasta(upload)
        upload.seek(0)
        return upload

    def clean(self):
        cleaned_data = super(PredictallForm, self).clean()
        plaintext = cleaned_data.get('query')
        file = cleaned_data.get('query_file')
        if plaintext and file:
            self._errors.setdefault('query', []).append('Please give the sequence in plain text or as a file upload, not both.')
        if 'query' not in self._errors and 'query_file' not in self._errors and not (plaintext or file):
            self._errors.setdefault('query', []).append('At least one sequence is required.')
        return cleaned_data

    def get_query_entries(self):
        if not self.is_valid():
            raise KeyError('Cannot get entries from invalid form')
        if self._entries is None:
            self._entries = clean_fasta(self.initial['query_file'].open())
        return self._entries


@permission_required("pconsc.access_predictalljob")
@transaction.atomic
def predictall(request):
    key_base = 'pconsc.predictall.submit_job'
    cached_uploads = CachedUploadManager.get_from_session(request.session, key_base, ['query_file'])
    ok_to_accept, form = get_form(PredictallForm, request, cached_uploads)
    if not ok_to_accept:
        cached_uploads.store_in_session()
        form_contents = FormContents(form, **form.annotations)
        return render(request, 'datisca/nodule_trans_blast.html', predictall_params(request, form_contents=form_contents))
    # Job accepted
    job = PredictallJob(status=JOB_STATUS_LEVEL_ACCEPTED)
    job.save()
    job = PredictallJob.objects.select_for_update().get(pk=job.id)
    job.log_create(request.user, 'Created in web interface.')
    job.submit(request.user,
               request.META['REMOTE_ADDR'],
               form.cleaned_data['name'],
               scheduler,
               form.get_query_entries(),
               hhblitsdb,
               jackhmmerdb)
    cached_uploads.clear_from_session()
    return redirect('jobs.views.show_results', job.slug)


#@permission_required("pconsc.access_api_predictalljob")
def api_predictall(request):
    if request.method == 'GET':
        help = dict(query='Protein sequence in fasta format.',
                    name='A name for your job.')
        return json_response(help)
    try:
        data = dict(simplejson.loads(request.body))
    except:
        return HttpResponse(status=400)
    form = PredictallForm(data, initial=dict(query_file=None))
    if not form.is_valid():
        return json_response(dict(complaints=form._errors), status=422)
    job = PredictallJob(status=JOB_STATUS_LEVEL_ACCEPTED)
    job.save()
    job.log_create(request.fido_api_user, 'Created in api.')
    job.submit(request.fido_api_user,
               request.META['REMOTE_ADDR'],
               form.cleaned_data['name'],
               scheduler,
               form.get_query_entries(),
               hhblitsdb,
               jackhmmerdb)
    return redirect(api_show_results, job.slug)


def predictall_results(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    job.update_status(request.user)
    if job.status == JOB_STATUS_LEVEL_DELETED:
        raise Http404('no such job')
    params = predictall_params(request, job=job)
    if job.is_alive:
        reload_time, interval = request.session.setdefault('pconsc_predictall', dict()).pop(job.slug, (0, 5))
        if reload_time <= time.time():
            reload_time = max(time.time() + 5, reload_time + interval)
            interval *= 2
        request.session['pconsc_predictall'][job.slug] = (reload_time, interval)
        request.session.modified = True
        params.update(timeout=reload_time - time.time())
        params.update(reload_time=reload_time, interval=interval)
        if os.path.isfile(job.workfile('log')):
            # Does not exist until pconsc starts running (eg: not in data
            # staging) Pull last 400 lines from log (there will about 150 in a
            # standard run).
            params.update(pconsc_log_text='\n'.join(open(job.workfile('log')).read().splitlines()[-400:]))
    return render(request, 'pconsc/predictall_results.html', params)
