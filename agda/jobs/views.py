import time

from django import forms
from django.db import transaction
from django.shortcuts import (render, redirect)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from agda.forms import get_form

from jobs.models import (JOB_STATUS_LEVEL_DELETED,
                         JOB_STATUS_LEVEL_FINISHED,
                         JOB_STATUS_LEVEL_ACCEPTED,
                         Job,
                         get_job_or_404,
                         update_status_for_jobs,)


from agda.views import require_nothing, package_template_dict


@login_required
def list_jobs(request):
    alive = (Job.objects.select_subclasses()
                .filter(user=request.user)
                .filter(status__gte=JOB_STATUS_LEVEL_ACCEPTED)
                .filter(status__lt=JOB_STATUS_LEVEL_FINISHED))
    update_status_for_jobs(request.user, alive)
    jobs = Job.objects.filter(user=request.user)\
              .exclude(status=JOB_STATUS_LEVEL_DELETED)\
              .order_by('-submission_date').select_subclasses()
    return render(request, 'agda/job/list.html', dict(jobs=jobs))


def generic_show_results(request, job):
    params = package_template_dict(request, package=job.tool.package, tool=job.tool, job=job)
    if job.is_alive:
        session_key = job.tool.name + '.generic_results.timeout'
        reload_time, interval = request.session.setdefault(session_key, dict()).pop(job.slug, (0, 5))
        if reload_time <= time.time():
            reload_time = max(time.time() + 5, reload_time + interval)
            interval *= 2
        request.session[session_key][job.slug] = (reload_time, interval)
        request.session.modified = True
        params.update(timeout=reload_time - time.time())
        params.update(reload_time=reload_time, interval=interval)
    return render(request, 'agda/job/results.html', params)


@require_nothing
def show_results(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    job.update_status(request.user)
    if job.status == JOB_STATUS_LEVEL_DELETED:
        raise Http404('no such job, you friggin')
    module, view = job.tool.results_view.rsplit('.', 1)
    tmp = __import__(module, globals(), locals(), [view])
    return getattr(tmp, view)(request, slug)


@require_nothing
def delete_job(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    ok_to_delete = False
    if not job.user or job.user == request.user:
        if request.method == "POST":
            job.update_status(request.user, JOB_STATUS_LEVEL_DELETED)
            messages.success(request, "The job has been deleted.")
            if request.user.is_authenticated():
                return redirect(list_jobs)
            return redirect('agda.views.top')
        ok_to_delete = True
    return render(request, 'agda/job/delete.html', dict(job=job, request=request, ok_to_delete=ok_to_delete))


@require_nothing
def delete_jobs(request):
    slugs = request.POST.getlist('slug')
    redirect_target = list_jobs if request.user.is_authenticated() else 'agda.views.top'
    if not slugs:
        messages.warning(request, 'You have not given any jobs to delete.')
        return redirect(redirect_target)
    jobs = Job.objects.filter(slug__in=slugs).select_for_update()
    with transaction.commit_manually():
        try:
            if not len(slugs) == len(jobs):
                raise Http404('no such job')
            for job in jobs:
                if job.user and job.user != request.user:
                    messages.error(request, 'You cannot delete jobs that belong to someone else.')
                    return redirect(redirect_target)
            for job in jobs:
                job.update_status(request.user, JOB_STATUS_LEVEL_DELETED)
        finally:
            transaction.commit()
    messages.success(request, "The jobs have been deleted.")
    return redirect(redirect_target)


@login_required
def take_job(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    if not job.user:
        if request.method == "POST":
            job.user = request.user
            job.save()
            job.log_change(request.user, "Changed user to %s." % request.user)
            messages.success(request, "You have taken ownership of the job.")
            return redirect(show_results, slug)
    return render(request, 'agda/job/take.html', dict(job=job, request=request))


class RenameJobForm(forms.Form):
    name = forms.CharField(max_length=100)


def rename_job(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    ok_to_rename, form = get_form(RenameJobForm, request, initial=dict(name=job.name))
    ok_to_rename &= job.user == request.user
    if not ok_to_rename:
        return render(request, 'agda/job/rename.html', dict(job=job, request=request, form=form))
    # OK to save.
    job.name = form.cleaned_data['name']
    job.save()
    job.log_change(request.user, "Changed name to %s." % job.name)
    messages.success(request, "The job has been renamed.")
    return redirect(list_jobs)
