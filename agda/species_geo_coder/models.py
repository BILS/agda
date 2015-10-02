import json
import os
import shutil

from django.db import models
from django.conf import settings
from django.template.loader import render_to_string


from agda.models import Package
from jobs.models import Job, slurm


# A representation of the current app
app_package = Package(
    view        = 'species_geo_coder.views.top',
    name        = 'SpeciesGeoCoder',
    displayname = 'SpeciesGeoCoder',
    description = 'A tool for large scale biogeographical data analysis',
)
app_package.register()


# One tool in the current app, copy these as needed
tool_1 = app_package.new_tool(
    view         = 'species_geo_coder.views.tool_1',
    results_view = 'species_geo_coder.views.tool_1_results',
    #api_view     = 'species_geo_coder.views.api_scan',
    name         = 'species_geo_coder/geocoder',
    displayname  = 'SpeciesGeoCoder',
    description  = 'A tool for large scale biogeographical data analysis'
)


class SpeciesGeoCoderJob(Job):
    files = dict(
        localities = 'localities.csv',
        polygons   = 'polygons.txt',
        outfile    = 'result.nxs',
    )
    tool = tool_1

    def on_submit(self, files, occurences, verbose, plot, *args, **kwargs):
        # Takes stuff from args and kwargs to generate submission
        script = 'runner.sh'

        run_script_parameters = self.files.copy()
        run_script_parameters['verbose'] = verbose
        run_script_parameters['plot'] = plot
        run_script_parameters['occurences'] = occurences

        self.write_workfile(script, render_to_string('species_geo_coder/runner.sh', run_script_parameters))
        job_script = self.workfile(script)

        self.write_workfile(self.files['localities'], files['localities'].read() )
        self.write_workfile(self.files['polygons'], files['polygons'].read() )

        res = dict()
        res['outfile'] = self.files['outfile']

        if plot:
            res['plot'] = 'plots.zip'

        self.result_files = res

        slurm.submit(self, job_script)


# All tools that require cluster resources should be represented by a Job class
# that inherits from jobs.models.Job
#class ToolJob(Job):
#    # The files dictionary should contain all the files needed for the job
#    files = dict(query='query.fasta',
#                 hmmpfam='mdrscan.hmmpfam',
#                 json='mdrscan.json')
#
#    tool = tool_1
#
#    # Permission stuff, in case the tool needs to be restricted
#    class Meta:
#        permissions = (
#            ("can_view", "Can view and submit mdr job"),
#        )
#
#    # You need to reimplement this one, this should generate a sbatch script
#    # for the cluster.
#    def on_submit(self, entries):
#        # What does statistics do?
#        self.statistics = json.dumps(dict(sequences=len(entries), residues=sum(len(e) for e in entries)))
#
#        # This takes whatever is entered into the submission, have to check this out.
#        self.write_workfile('query', entries.to_str())
#        script = 'mdrscan.sh'
#        db = os.path.join(settings.DATA_ROOT, 'pub', 'mdr', '2010.1', 'mdr.pfam.gz')
#        self.write_workfile(script, render_to_string('mdr/mdrscan.sh', dict(db=db)))
#        self.write_workfile('family_data.json', parse_mdrscan.FamilyData.dumps(Family.objects.all()))
#        shutil.copy(parse_mdrscan.__file__.rstrip('oc'), self.workdir)
#        self.result_files = self.files
#        slurm.submit(self, self.workfile(script))


# Create extra django models here, in case they are needed for the app

