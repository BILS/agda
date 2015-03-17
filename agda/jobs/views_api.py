import json
import os

from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import Http404, HttpResponse

from jobs.models import (JOB_STATUS_LEVEL_DELETED,
                         JOB_STATUS_LEVEL_FINISHED,
                         JOB_STATUS_LEVEL_ACCEPTED,
                         Job,
                         get_job_or_404,
                         update_status_for_jobs,)

from agda.utils import model_dict

from agda.views import (require_nothing, api_require_nothing, json_response,
                        json_datetime_encoder)


def api_generic_show_results(request, job):
    job_info = model_dict(job, ['id', 'parameters', 'status', 'status_name', 'submission_date', 'start_date', 'completion_date'])
    job_info['tool'] = job.tool.displayname
    job_info['job'] = job.slug
    if job.status == JOB_STATUS_LEVEL_FINISHED:
        _url = lambda path: request.build_absolute_uri(os.path.join(job.resultdir_url, path))
        job_info['results'] = dict((name, _url(path)) for name, path in job.result_files.items())
    return json_response(job_info, default=json_datetime_encoder)


def api_list_jobs(request):
    user = request.agda_api_user
    alive = (Job.objects.select_subclasses()
                .filter(user=user)
                .filter(status__gte=JOB_STATUS_LEVEL_ACCEPTED)
                .filter(status__lt=JOB_STATUS_LEVEL_FINISHED))
    update_status_for_jobs(user, alive)
    jobs = (Job.objects.select_subclasses()
            .filter(user=user)
            .exclude(status=JOB_STATUS_LEVEL_DELETED)
            .order_by('-submission_date'))

    def job_info(job):
        info = model_dict(job, ['id', 'status', 'status_name', 'submission_date', 'start_date', 'completion_date'])
        info['results'] = request.build_absolute_uri(reverse(api_show_results, args=[job.slug]))
        info['tool'] = job.tool.displayname
        return info
    return json_response([job_info(j) for j in jobs], default=json_datetime_encoder)


@api_require_nothing
def api_show_results(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    job.update_status(request.user)
    if job.status == JOB_STATUS_LEVEL_DELETED:
        raise Http404('no such job')
    module, view = job.tool.api_results_view.rsplit('.', 1)
    tmp = __import__(module, globals(), locals(), [view])
    return getattr(tmp, view)(request, slug)


@require_nothing
def api_delete_jobs(request):
    if request.method != 'POST':
        return json_response(dict(jobs=['list of job ids to delete, e.g:', '543d654ddtetTdew89WE']))
    is_ok, p = get_parameters_or_response(request.body, ['jobs'])
    if not is_ok:
        return p
    slugs = p['jobs']
    jobs = Job.objects.filter(slug__in=slugs).select_for_update()
    with transaction.commit_manually():
        try:
            if not len(slugs) == len(jobs):
                raise Http404('no such job')
            for job in jobs:
                if job.user and job.user != request.user:
                    return HttpResponse(status=403)
            for job in jobs:
                job.update_status(request.user, JOB_STATUS_LEVEL_DELETED)
        finally:
            transaction.commit()
    json_response(dict(success='Jobs deleted.'))


@api_require_nothing
def api_delete_job(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    if job.status == JOB_STATUS_LEVEL_DELETED:
        raise Http404('no such job')
    if request.method != 'POST':
        return json_response(dict(delete='Set to true to delete.'))
    if job.user and job.user != request.agda_api_user:
        return json_response(dict(complaints='This job is not yours.'), status=403)
    job.update_status(request.user, JOB_STATUS_LEVEL_DELETED)
    return json_response(dict(success='Job deleted.'))


def api_take_job(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    if job.status == JOB_STATUS_LEVEL_DELETED:
        raise Http404('no such job')
    if job.user:
        if job.user == request.agda_api_user:
            return json_response(dict(complaints='This job is already yours.'), status=409)
        return json_response(dict(complaints='This job belongs to someone else.'), status=403)
    if request.method != 'POST':
        return json_response(dict(take='Set to true to take ownership of this job.'))
    try:
        assert json.loads(request.body)['take']
    except:
        return HttpResponse(status=400)
    job.user = request.agda_api_user
    job.save()
    job.log_change(request.agda_api_user, "Changed user to %s." % job.user)
    return json_response(dict(success='You have taken ownership of the job.'))


def api_rename_job(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    if job.user != request.agda_api_user:
        return json_response(dict(complaints='This job is not yours.'), status=403)
    if request.method != 'POST':
        return json_response(dict(name='A new name for this job.'))
    try:
        name = json.loads(request.body)['name']
    except:
        return HttpResponse(status=400)
    if not name:
        return json_response(dict(complaints='No name supplied.'), status=403)
    job.name = name
    job.save()
    job.log_change(request.agda_api_user, "Changed user to %s." % job.user)
    return json_response(dict(success='Job has been renamed.'))


def get_parameters_or_response(json_dict_string, required=[], defaults={}):
    """Load dict from json string, check that required fields exist.

    The key _required has a list of the values, in the given order.

    Returns
    -------
    HttpResponse : if malformed or fields missing.
    data : json dict

    """
    data = dict(defaults)
    try:
        data.update(json.loads(json_dict_string))
    except:
        return HttpResponse(status=400)
    data['_required'] = []
    for field in required:
        try:
            data['_required'].append(data[field])
        except:
            return json_response(dict(complaints='required field %r not supplied' % field), status=422)
    return data
