from datetime import datetime
import json
import os
import random
import shutil
import string
import subprocess
import sys
import traceback
import logging

import pytz

from django.db import (models,
                       transaction)
from django.conf import settings
from django.http import Http404

from agda.models import AgdaModelMixin
from agda.utils import ModelDiffer
from agda.settings.local import AUTH_USER_MODEL

from model_utils.managers import InheritanceManager
from profiles.models import get_user_or_anonymous

logger = logging.getLogger(__name__)

### Jobs ###

JOB_STATUS_LEVEL_REJECTED = -100
JOB_STATUS_LEVEL_ACCEPTED = 0
JOB_STATUS_LEVEL_SUBMITTED = 10
JOB_STATUS_LEVEL_QUEUED = 20
JOB_STATUS_LEVEL_RUNNING = 30
JOB_STATUS_LEVEL_FAILED = -1
JOB_STATUS_LEVEL_DELETED = -10
JOB_STATUS_LEVEL_FINISHED = 1000
job_status_levels = {-100: 'Rejected',
                     0:    'Accepted',
                     10:   'Submitted',
                     20:   'Queued',
                     30:   'Running',
                     -1:   'Failed',
                     -10:  'Deleted',
                     1000: 'Finished'
                     }


### Schedulers ###
class Scheduler(object):
    def submit(self, job):
        """Submit a job to the scheduler."""
        pass

    def cancel(self, job):
        """Make token effort to cancel a scheduled job."""
        pass

    def status(self, job):
        """Return scheduler status, start time, end time for the given job.

        Start/end times are None for jobs that have not started/ended yet.
        """
        pass

    def get_job_states(self, jobs):
        """Query the scheduler and return (job, (status, start, end)) tuples.

        Start/end times are None for jobs that have not started/ended yet.
        """
        pass

schedulers = dict()


class Slurm(Scheduler):
    state_map = {
        "PD":          JOB_STATUS_LEVEL_QUEUED,
        "PENDING":     JOB_STATUS_LEVEL_QUEUED,
        "CF":          JOB_STATUS_LEVEL_QUEUED,
        "CONFIGURING": JOB_STATUS_LEVEL_QUEUED,

        "R":           JOB_STATUS_LEVEL_RUNNING,
        "RUNNING":     JOB_STATUS_LEVEL_RUNNING,
        "S":           JOB_STATUS_LEVEL_RUNNING,
        "SUSPENDED":   JOB_STATUS_LEVEL_RUNNING,
        "CG":          JOB_STATUS_LEVEL_RUNNING,
        "COMPLETING":  JOB_STATUS_LEVEL_RUNNING,

        "CD":          JOB_STATUS_LEVEL_FINISHED,
        "COMPLETED":   JOB_STATUS_LEVEL_FINISHED,

        "CA":          JOB_STATUS_LEVEL_FAILED,
        "CANCELLED":   JOB_STATUS_LEVEL_FAILED,
        "CANCELLED+":  JOB_STATUS_LEVEL_FAILED,
        "F":           JOB_STATUS_LEVEL_FAILED,
        "FAILED":      JOB_STATUS_LEVEL_FAILED,
        "NF":          JOB_STATUS_LEVEL_FAILED,
        "NODE_FAIL":   JOB_STATUS_LEVEL_FAILED,
        "PR":          JOB_STATUS_LEVEL_FAILED,
        "PREEMPTED":   JOB_STATUS_LEVEL_FAILED,
        "TO":          JOB_STATUS_LEVEL_FAILED,
        "TIMEOUT":     JOB_STATUS_LEVEL_FAILED,
    }

    time_format = "%Y-%m-%dT%H:%M:%S"

    def submit(self, job, job_script, job_args=[], time=1440, nodes=1, tasks=1, slurm_args=[], stdin=None, stdout='std.out', stderr='std.err'):
        stdout = os.path.join(job.workdir, stdout)
        if not stdout.startswith(job.workdir):
            raise ValueError('job stdout file is not in job workdir')
        stderr = os.path.join(job.workdir, stderr)
        if not stdout.startswith(job.workdir):
            raise ValueError('job stderr file is not in job workdir')
        argv = ['sbatch', '-D', job.workdir, '-o', stdout, '-e', stderr,
                '-N', str(nodes), '-n', str(tasks), '-t', str(time)]
        if stdin is not None:
            stdin = os.path.join(job.workdir, stdin)
            if not input.startswith(job.workdir):
                raise ValueError('job stdin file is not in job workdir')
            argv.extend(['-i', stdin])
        argv.extend(slurm_args)
        argv.append(job_script)
        argv.extend(job_args)
        output = call(argv)
        # sbatch should return e.g. "Submitted batch job 525112", fail if incomprehensible.
        job.scheduler_id = str(int(output.split()[-1]))
        job.status = JOB_STATUS_LEVEL_SUBMITTED
        open(job.workfile('slurm-' + job.scheduler_id), 'w')
        logger.info('job id=%(id)s:%(slug)s submitted as slurm job %(scheduler_id)s.',
                    dict(id=job.id, slug=job.slug, scheduler_id=job.scheduler_id))

    def cancel(self, job):
        if job.scheduler_id is not None:
            try:
                call(['scancel', job.scheduler_id])
            except:
                pass

    def parse_status(self, slurm_state, slurm_start, slurm_end, slurm_id=None, jobmap=None):
        start = None
        end = None
        status = self.state_map[slurm_state.strip()]
        local_timezone = pytz.timezone("Europe/Stockholm")
        if status >= JOB_STATUS_LEVEL_RUNNING:
            start = datetime.strptime(slurm_start, self.time_format)
            start = local_timezone.localize(start)
        if status >= JOB_STATUS_LEVEL_FINISHED or status < 0:
            end = datetime.strptime(slurm_end, self.time_format)
            end = local_timezone.localize(end)
        state = (status, start, end)
        if slurm_id:
            return (jobmap[int(slurm_id)], state)
        return state

    def status(self, job):
        argv = ['sacct', '-n', '--format=State,Start,End', '-j', job.scheduler_id]
        output = call(argv).split()
        if len(output) >= 3:
            return self.parse_status(*output[0:3])
        argv = ['squeue', '-t', 'all', '-ho', '%t %S %e', '-j', job.scheduler_id]
        return self.parse_status(*call(argv).split())

    def get_job_states(self, jobs):
        jobs = [j for j in jobs if j.scheduler_id is not None]
        ids = ','.join(j.scheduler_id for j in jobs if j.is_alive)
        jobmap = dict((int(j.scheduler_id), j) for j in jobs)
        argv = ['squeue', '-t', 'all', '-ho', '%t %S %e %i', '-j', ids]
        job_states = []
        for line in call(argv).splitlines():
            words = line.split()
            if not words:
                continue
            job_states.append(self.parse_status(*words, jobmap=jobmap))
        return job_states

slurm = Slurm()
schedulers.update(slurm=slurm)


class Slug(object):
    """Job slug class to generate hard to guess slug.

    What is a slug?
    http://stackoverflow.com/questions/427102/what-is-a-slug-in-django
    A job slug is a valid uniq valid URL for a job.
    This class create a valid random char to use as slug in jobs
    """
    chars = string.digits + string.ascii_lowercase
    length = 20
    regex = "[%s]{%d}" % (chars, length)

    @classmethod
    def generate(cls):
        return ''.join(random.choice(cls.chars) for i in range(cls.length))

    @classmethod
    def validate(cls, slug):
        if len(slug) != cls.length:
            raise ValueError("incorrect slug length")
        if False in (c in cls.chars for c in slug):
            raise ValueError("slug contains illegal characters")


# Helper dict for def get_jobdir to get right jobdir path
jobdirs = dict(error=settings.ERRORDIR_ROOT, results=settings.RESULTDIR_ROOT, work=settings.WORKDIR_ROOT)


def get_jobdir(slug, dirtype='work'):
    """Function to get jobdir path

    Parameters
    ----------
    slug : A job slug
    dirtype : The dirtype defined in the helper dict jobdirs

    Returns
    -------
    path : a os path dir
    """
    Slug.validate(slug)
    return os.path.join(jobdirs.get(dirtype), str(slug))


def get_resultdir_url(slug):
    """Function to get the resultdir url

    Parameters
    ----------
    slug : A job slug

    Returns
    -------
    url : a os path plus trailing "/" to make it a valid URL
    """
    Slug.validate(slug)
    return os.path.join(settings.RESULTDIR_URL, str(slug)) + '/'


def json_field_wrapper(name, json_default=None):
    """Helper boilerplate function for proper JSON field manipulation


    Parameters
    ----------
    name : name of JSON field object

    Returns
    -------
    property ; with json getter and setter
    """
    def getter(obj):
        value = getattr(obj, name)
        if value is not None:
            value = json.loads(value, json_default)
        return value

    def setter(obj, value):
        if value is not None:
            value = json.dumps(value, json_default)
        setattr(obj, name, value)

    return property(getter, setter)


@transaction.commit_manually()
def update_status_for_jobs(user, job_query_set):
    """Update status for multiple jobs.

    Aggregates jobs with same scheduler and uses .get_job_states(), in order to
    reduce overhead from communication with schedulers.
    """
    job_query_set.select_for_update()
    try:
        sched = dict()
        for job in job_query_set:
            sched.setdefault(schedulers[job.scheduler], []).append(job)
        for scheduler, scheduler_jobs in sched.items():
            states = scheduler.get_job_states(scheduler_jobs)
            for job, (status, start_time, end_time) in states:
                job.update_status(user, status, start_time, end_time)
    finally:
        transaction.commit()


def call(argv):
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errors = p.communicate()
    if p.returncode != 0:
        raise ValueError('%s command failed: %s, stdout: %s, stderr: %s' % (argv[0], argv, output, errors))
    return output


class Job(models.Model, AgdaModelMixin):

    def __init__(self, *args, **kw):
        super(Job, self).__init__(*args, **kw)
        slug = kw.get('slug')
        if len(args) >= 2:
            if slug:
                raise TypeError("__init__() got multiple values for keyword argument 'slug'")
            slug = args[1]
        if not slug:
            slug = Slug.generate()
            while Job.objects.filter(slug=slug):
                slug = Slug.generate()
        self.slug = slug

    slug = models.CharField(max_length=Slug.length, unique=True)
    user = models.ForeignKey(AUTH_USER_MODEL, blank=True, null=True)  # Blank for anonymous jobs.
    name = models.TextField(blank=True, null=True)
    submission_ip = models.IPAddressField(blank=True, null=True)
    submission_date = models.DateTimeField('submission date', blank=True, null=True)
    start_date = models.DateTimeField('start date', blank=True, null=True)
    completion_date = models.DateTimeField('completion date', blank=True, null=True)
    status = models.IntegerField(default=JOB_STATUS_LEVEL_REJECTED)
    reason = models.TextField(blank=True, null=True)
    scheduler = models.TextField(default='slurm', blank=True, null=True)
    scheduler_id = models.TextField(blank=True, null=True)
    result_files_json = models.TextField(blank=True, null=True)
    parameters_json = models.TextField(blank=True, null=True)
    statistics_json = models.TextField(blank=True, null=True)

    tool = None
    files = dict()

    result_files = json_field_wrapper('result_files_json')
    parameters = json_field_wrapper('parameters_json')
    statistics = json_field_wrapper('statistics_json')

    errordir = property(lambda self: get_jobdir(self.slug, 'error'))
    resultdir = property(lambda self: get_jobdir(self.slug, 'results'))
    resultdir_url = property(lambda self: get_resultdir_url(self.slug))
    results_url = property(lambda self: self.tool.results_url(self))
    workdir = property(lambda self: get_jobdir(self.slug, 'work'))

    status_name = property(lambda self: job_status_levels[self.status].capitalize())
    is_alive = property(lambda self: JOB_STATUS_LEVEL_ACCEPTED <= self.status < JOB_STATUS_LEVEL_FINISHED)

    def __unicode__(self):
        return u"%s:%s" % (self.id, self.slug)

    # Get an InheritanceQuerySet for Jobs in their proper subclasses.
    objects = InheritanceManager()

    def log_action(self, action_flag, user, message, object_repr):
        """Allow logging of anonymously submitted jobs."""
        user = get_user_or_anonymous(user)
        super(Job, self).log_action(action_flag, user, message, object_repr)

    def workfile(self, path):
        if path in self.files:
            path = self.files[path]
        return os.path.join(self.workdir, path)

    def resultfile(self, path):
        if self.result_files and path in self.result_files:
            path = self.result_files[path]
        elif path in self.files:
            path = self.files[path]
        return os.path.join(self.resultdir, path)

    def make_jobdir(self, dirtype):
        """Convenience method for creating jobdir in proper place with right
        permissions.

        Full rights should be bestowed to owner, while group should have at
        least read and execute rights, in order to allow agda admin to do
        painless autopsy on failed jobs.  Others should have no rights to any
        jobdir.
        """
        if dirtype not in ('error', 'results', 'work'):
            raise ValueError('no such dirtype')
        os.mkdir(get_jobdir(self.slug, dirtype), 0750)

    def remove_jobdir(self, dirtype):
        if dirtype not in ('error', 'results', 'work'):
            raise ValueError('no such dirtype')
        d = get_jobdir(self.slug, dirtype)
        if os.path.exists(d):
            shutil.rmtree(d)

    def move_workdir_to_errordir(self):
        if os.path.exists(self.workdir):
            shutil.move(self.workdir, self.errordir)

    def write_workfile(self, path, contents):
        if not os.path.isdir(self.workdir):
            self.make_jobdir('work')
        open(self.workfile(path), 'w').write(contents)

    def save_resultfile(self, src, dst=None):
        """Convenience method for copying a file or directory from self.workdir
        to self.resultdir.

        src is a path relative to self.workdir, and dst is a path relative to
        self.resultdir and defaults to src if not set. src can also be an
        absolute path, but must refer to something under self.workdir. This
        method uses shutil.copytree and has the same limitations.
        """
        src = os.path.join(self.workdir, src)
        if not src.startswith(self.workdir):
            raise ValueError('src not in workdir')
        if dst is None:
            dst = src[len(self.workdir) + 1:]
        dst = os.path.join(self.resultdir, dst)
        if not dst.startswith(self.resultdir):
            raise ValueError('dst not in resultdir')
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            dir = os.path.dirname(dst)
            if not os.path.isdir(dir):
                os.makedirs(dir, 0750)
            shutil.copy2(src, dst)

    def submit(self, user, submission_ip, name, *args, **kw):
        """Boilerplate logging and error handling around job submission.

        log_only_field_name_for is a list of field names that should only be
        logged by name if changed. Default is ['statistics'].

        This method:

        - sets status, user, name, submission_ip and submission_date
        - calls on_submit(\\*args, \\*\\*kw)
        - calls .save()
        - logs changes.
        - calls register_error() on exceptions.

        It is up to .on_submit() to do all useful work with job preparation and
        actual submission to the scheduler.
        """
        log_only_field_name_for = kw.get('log_only_field_name_for', ['statistics'])
        diff = ModelDiffer(self)
        try:
            if not name:
                name = self.tool.displayname + ' job'
            self.name = name
            self.status = JOB_STATUS_LEVEL_SUBMITTED
            self.submission_date = datetime.now()
            self.submission_ip = submission_ip
            if user.is_authenticated():
                self.user = user
            self.on_submit(*args, **kw)
        except:
            self.register_error(user, 'submission failed')
        finally:
            diff.update(self)
            self.log_change(user, diff.get_change_message(log_only_field_name_for))
            self.save()

    def on_submit(self):
        """Prepare files and submit job. Called by .submit().

        This method does nothing, so subclasses should override this method
        (perhaps cooperatively) do actual work.
        """

    def cancel(self):
        """Remove the job from the scheduler."""
        if self.is_alive:
            schedulers[self.scheduler].cancel(self)

    def check_status(self):
        """Check with scheduler and return job state (status, start, end).

        Non-running jobs return existing (status, start_date, comletion_date).

        The current default is to use the slurm scheduler.
        """
        if self.is_alive:
            return schedulers[self.scheduler].status(self)
        return (self.status, self.start_date, self.completion_date)

    def register_error(self, user, reason, admin_details=None):
        """Called when a job has failed due to an error.

        If admin_details is None, traceback.format_exc() (if any) will be used
        instead.

        This method does:

    - cancel live jobs.
        - call on_status_change(JOB_STATUS_LEVEL_FAILED)
        - remove resultdir
        - move workdir to errordir
        - update status, completion_time, reason.
        - error log admin_details.
        - call .save()

        This method does not log any changes

        """
        if admin_details is None and sys.exc_info()[1] is not None:
            admin_details = traceback.format_exc()
        self.cancel()
        self.remove_jobdir('results')
        self.move_workdir_to_errordir()
        logger.error('Job %s - %s - %s' % (unicode(self), reason, admin_details))
        self.status = JOB_STATUS_LEVEL_FAILED
        self.reason = reason

    def update_status(self, user, status=None, start_date=None, completion_date=None, diff=None):
        """Update job status.

        Use status=None to force a running job to check for status updates with
        the scheduler.

        This method should do all necessary work to update job status:

        - move/delete resultfiles
        - update status, reason, start/competion dates
        - call save()
        - call register_error() on on_status_change() exceptions
        - log changes
        """
        if diff is None:
            diff = ModelDiffer(self)
        if status is None:
            status, start_date, completion_date = self.check_status()
        if status == self.status:
            return
        if start_date != self.start_date:
            self.start_date = start_date
        if completion_date != self.completion_date:
            self.completion_date = completion_date
        try:
            self.on_status_changed(status)
            self.status = status
        except:
            reason = 'Error during status change to %s.' % job_status_levels[status].capitalize()
            self.register_error(user, reason)
        finally:
            self.save()
            diff.update(self)
            self.log_change(user, diff.get_change_message())
        if self.status < 0:
            self.cancel()
        if self.status == JOB_STATUS_LEVEL_DELETED:
            self.remove_jobdir('error')
            self.remove_jobdir('results')
            self.remove_jobdir('work')
        elif self.status == JOB_STATUS_LEVEL_FAILED:
            self.remove_jobdir('results')
            self.move_workdir_to_errordir()
        elif self.status == JOB_STATUS_LEVEL_FINISHED:
            self.remove_jobdir('work')

    def on_status_changed(self, status):
        """Called by update_status() on job status change.

        Callback for jobs that need to take special steps for any status
        transitions. For example, postprocessing or copying result files to
        .resultdir in case of finished jobs. Any exceptions raised will be
        treated as job failure.

        This method should not:

        - cancel deleted/failed jobs.
        - delete workdir for finished jobs.
        - move workdir to errordir for failed jobs.
        - update status, start_time and completion_time.
        - log changes
        - call .save()

        Since update_status() already does all of that.
        """
        if status == JOB_STATUS_LEVEL_FINISHED:
            for file in self.result_files.values():
                self.save_resultfile(file)


def get_job_or_404(select_for_update=False, **kw):
    jobs = Job.objects.filter(**kw).select_subclasses()
    if select_for_update:
        jobs.select_for_update()
    if not jobs:
        raise Http404('No such job')
    if jobs[0].status == JOB_STATUS_LEVEL_DELETED:
        raise Http404('No such job')
    return jobs[0]
