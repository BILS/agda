import json
import os
import shutil

from django.conf import settings
from django.db import models
from django.template.loader import render_to_string


from agda.models import Package
from agda.query import MySQLFulltextSearchQuerySet
from jobs.models import Job, slurm

import parse_mdrscan

mdr_package = Package(
    view='mdr.views.top',
    name='mdr',
    nickname='MDR',
    description='MDR family database and tools.')
mdr_package.register()

mdrscan_tool = mdr_package.new_tool(
    view='mdr.views.scan',
    results_view='mdr.views.scan_results',
    api_view='mdr.views.api_scan',
    name='mdr/mdrscan',
    nickname='MDRScan',
    description='Scan a sequence and classify any known present MDR domains.')

mdrsearch_tool = mdr_package.new_tool(
    view='mdr.views.search',
    api_view='mdr.views.api_search',
    name='mdr/mdrsearch',
    nickname='MDRSearch',
    description='Search the MDR database.')

mdrlookup_tool = mdr_package.new_tool(
    view='mdr.views.family_lookup',
    api_view='mdr.views.api_family_lookup',
    name='mdr/mdrlookup',
    nickname='MDRLookup',
    description='Show information on an MDR family.')


class MDRScanJob(Job):
    files = dict(query='query.fasta',
                 hmmpfam='mdrscan.hmmpfam',
                 json='mdrscan.json')

    tool = mdrscan_tool

    class Meta:
        permissions = (
            ("can_view", "Can view and submit mdr job"),
        )

    def on_submit(self, entries):
        self.statistics = json.dumps(dict(sequences=len(entries), residues=sum(len(e) for e in entries)))
        self.write_workfile('query', entries.to_str())
        script = 'mdrscan.sh'
        db = os.path.join(settings.DATA_ROOT, 'pub', 'mdr', '2010.1', 'mdr.pfam.gz')
        self.write_workfile(script, render_to_string('mdr/mdrscan.sh', dict(db=db)))
        self.write_workfile('family_data.json', parse_mdrscan.FamilyData.dumps(Family.objects.all()))
        shutil.copy(parse_mdrscan.__file__.rstrip('oc'), self.workdir)
        self.result_files = self.files
        slurm.submit(self, self.workfile(script))


class Family(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=10)
    representative_description = models.TextField(blank=True, null=True)
    representative_id = models.CharField(max_length=12)
    size = models.IntegerField()
    swissprot_members = models.IntegerField()
    average_pcid = models.FloatField()
    in_human = models.BooleanField()
    in_kingdom_eukaryota = models.BooleanField()
    in_kingdom_bacteria = models.BooleanField()
    in_kingdom_archaea = models.BooleanField()
    in_division_unassigned = models.BooleanField()
    in_division_synthetic = models.BooleanField()
    in_division_environmental_samples = models.BooleanField()
    in_division_phages = models.BooleanField()
    in_division_viruses = models.BooleanField()
    in_division_bacteria = models.BooleanField()
    in_division_plants = models.BooleanField()
    in_division_invertebrates = models.BooleanField()
    in_division_vertebrates = models.BooleanField()
    in_division_mammals = models.BooleanField()
    in_division_rodents = models.BooleanField()
    in_division_primates = models.BooleanField()
    zn1 = models.FloatField()
    zn2 = models.FloatField()
    nad = models.FloatField()
    nadp = models.FloatField()
    min_score = models.FloatField()
    max_score = models.FloatField()

    def __str__(self):
        if self.name:
            return self.id + ' - ' + self.name
        return self.id


class Member(models.Model):
    family_id = models.CharField(max_length=10)
    rank = models.IntegerField()
    family_name = models.CharField(max_length=10)
    source_database = models.CharField(max_length=16)
    uniprot_ac = models.CharField(max_length=6)
    uniprot_id = models.CharField(max_length=12)
    start = models.IntegerField()
    stop = models.IntegerField()
    score = models.FloatField()
    sequence_length = models.IntegerField()
    species = models.TextField()
    species_common_name = models.TextField(blank=True, null=True)
    kingdom = models.CharField(max_length=1)
    taxonomic_division = models.CharField(max_length=3)
    description = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    objects = MySQLFulltextSearchQuerySet.as_manager()
    fulltext_indexes = dict(description=(description,),
                            default=(family_id,
                                     family_name,
                                     source_database,
                                     uniprot_ac,
                                     uniprot_id,
                                     species,
                                     species_common_name,
                                     description,
                                     comment))

    def __str__(self):
        return "%s - %s" % (self.family_id, self.rank)
