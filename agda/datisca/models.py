import shutil

from django.template.loader import render_to_string

from agda.models import Package
from jobs.models import Job, slurm

from core import fasta
import os
import parse_blast

datisca_package = Package(
    view='datisca.views.top',
    name='datisca',
    displayname='Datisca',
    description='Tools and databases related to the Datisca glomerata nodule transcriptome project.',
)
datisca_package.register()

datisca_nodule_blast_tool = datisca_package.new_tool(
    name='datisca/nodule_trans_blast',
    displayname='NoduleBlast',
    description='Sequence similarity search in the Datisca glomerata nodule transcriptome.',
    api_view='datisca.views.api_nodule_trans_blast',
    view='datisca.views.nodule_trans_blast',
    results_view='datisca.views.nodule_trans_blast_results',
)


class DatiscaNoduleBlastJob(Job):
    tool = datisca_nodule_blast_tool
    files = dict(query='query.fasta',
                 blast='results.blast',
                 json='noduleblast.json',
                 hits='hits.fa')

    def on_submit(self, program, entries, db, evalue):
        self.statistics = dict(sequences=len(entries), characters=sum(len(e) for e in entries))
        dbnick = 'reads'
        if db.endswith('all'):
            dbnick = 'reads'
        if 'contigs' in db:
            dbnick = 'contigs'
        if 'assembly' in db:
            dbnick = 'assembly'
        self.parameters = dict(program=program, db=dbnick, evalue=evalue)
        self.result_files = self.files
        self.write_workfile('query', entries.to_str())
        script = 'blast.sh'
        params = dict(db=db,
                      evalue=evalue,
                      out=self.files['blast'],
                      program=program,
                      query=self.files['query'])
        self.write_workfile(script, render_to_string('datisca/blast.sh', params))
        shutil.copy(parse_blast.__file__.rstrip('oc'), self.workdir)

        ## Copy the core/fasta.py thingy TODO fix this
        self.make_workdir('core')
        shutil.copy(fasta.__file__.rstrip('oc'), os.path.join(self.workdir, 'core'))
        self.write_workfile('core/__init__.py', "")

        self.result_files = self.files
        slurm.submit(self, self.workfile(script))
