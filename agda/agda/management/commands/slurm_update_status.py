from django.core.management.base import BaseCommand

from jobs.models import (JOB_STATUS_LEVEL_ACCEPTED,
                         JOB_STATUS_LEVEL_FINISHED,
                         Job,
                         update_status_for_jobs)

from profiles.models import get_system_user

system_user = get_system_user()


class Command(BaseCommand):
    args = '<slug slug ...>'
    help = 'Update status for alive slurm jobs.'

    def handle(self, *slugs, **options):
        jobs = (Job.objects.select_subclasses()
                .filter(scheduler='slurm')
                .filter(status__gte=JOB_STATUS_LEVEL_ACCEPTED)
                .filter(status__lt=JOB_STATUS_LEVEL_FINISHED))
        if slugs:
            jobs = jobs.filter(slug__in=slugs)
        if jobs:
            print "Updating status for %s jobs:" % len(jobs)
            print '\n'.join("%s:%s:%s" % (j.id, j.slug, j.scheduler_id)
                            for j in jobs)
            update_status_for_jobs(get_system_user(), jobs)
