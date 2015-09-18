from datetime import datetime
from hashlib import md5
import os
import shutil
import tarfile

from django.core.cache import get_cache

from django.template.loader import render_to_string

from agda.forms import FastaCleaner
from agda.models import Package
from jobs.models import (Job,
                         JOB_STATUS_LEVEL_FINISHED,
                         schedulers)

import parse_pconsc


pconsc_package = Package(
    permission='pconsc.access_predictalljob',
    view='pconsc.views.top',
    name='pconsc',
    displayname='PconsC',
    description='Tools and databases related to the PconsC protein structure contact predictor.',
)
pconsc_package.register()

predictall_tool = pconsc_package.new_tool(
    name='pconsc/predictall',
    displayname='PredictAll',
    description='Full contact prediction from single sequence, including database search.',
    api_view='pconsc.views.api_predictall',
    view='pconsc.views.predictall',
    results_view='pconsc.views.predictall_results',
)

clean_fasta = FastaCleaner(default_id='query_sequence', min_sequences=0, max_sequences=1).clean
cache = get_cache('filesystem')


class PredictallJob(Job):
    tool = predictall_tool
    files = dict(query='query.fasta',
                 out='query.fasta.pconsc.out',
                 image='query.fasta.pconsc.out.cm.png',
                 log='log.txt',
                 intermediaries='intermediary_predictions.tgz',
                 image2='query.fasta.pconsc2.out.cm.png',
                 out2='query.fasta.pconsc2.out')

    class Meta:
        permissions = (
            ("access_predictalljob", "Can access predictalljob"),
        )

    def cache_key(self, sequence):
        """Needs self.parameters to be set."""
        hex = md5(sequence).hexdigest()
        template = '{pconsc:%r,md5seq:%r,hhdb:%r,jhdb:%r}'
        return template % ('0.2.3', hex, str(self.parameters['hhblitsdb']), str(self.parameters['jackhmmerdb']))

    def copy_cached_results(self, cached_results):
        f = open(self.resultfile('intermediaries'), 'w+')
        f.write(cached_results)
        f.seek(0)
        tf = tarfile.open(fileobj=f, mode='r|gz')
        members = (info for info in tf if os.path.splitext(info.name)[1] in ['.out', '.png', '.txt'])
        tf.extractall(self.resultdir, members)
        tf.close()
        f.close()
        tmpdir = os.path.splitext(self.resultfile('intermediaries'))[0]
        for name in os.walk(tmpdir).next()[2]:
            shutil.move(os.path.join(tmpdir, name), self.resultdir)
        shutil.rmtree(tmpdir)

    def on_submit(self, scheduler, query, hhblitsdb, jackhmmerdb):
        sequence = query[0].sequence
        self.scheduler = scheduler
        self.statistics = dict(length=len(sequence))
        self.parameters = dict(hhblitsdb=hhblitsdb, jackhmmerdb=jackhmmerdb)
        self.result_files = self.files
        self.write_workfile('query', query.to_str())

        # Cache hit means instafinished job.
        cached_results = cache.get(self.cache_key(sequence))
        if cached_results:
            self.make_jobdir('results')
            self.copy_cached_results(cached_results)
            self.save_resultfile('query')
            self.remove_jobdir('work')
            self.status = JOB_STATUS_LEVEL_FINISHED
            self.start_date = datetime.now()
            self.completion_date = datetime.now()
            return

        script = 'predictall.sh'
        params = dict(self.files,
                      hhblitsdb=hhblitsdb,
                      jackhmmerdb=jackhmmerdb)
        self.write_workfile(script, render_to_string('pconsc/predictall.sh', params))
        shutil.copy(parse_pconsc.__file__.rstrip('oc'), self.workdir)
        self.result_files = self.files
        #schedulers[scheduler].submit(self, self.workfile(script), tasks=16, time=1440)
        schedulers[scheduler].submit(self, self.workfile(script), tasks=2, time=1440)

    def on_status_changed(self, status):
        if status != JOB_STATUS_LEVEL_FINISHED:
            return
        for file in self.result_files.values():
            self.save_resultfile(file)
        # Cache this stuff a year.
        cache_seconds = 60*60*24*365
        sequence = clean_fasta(open(self.resultfile('query')).read())[0].sequence
        cache.add(self.cache_key(sequence), open(self.resultfile('intermediaries')).read(), cache_seconds)
