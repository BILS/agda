#from django.shortcuts import render
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect, render

from agda.views import package_template_dict
from jobs.models import (JOB_STATUS_LEVEL_ACCEPTED,
                         JOB_STATUS_LEVEL_FINISHED,
                         get_job_or_404)

from species_geo_coder.models import app_package, SpeciesGeoCoderJob
from species_geo_coder.forms import SpeciesGeoCoderForm

from species_geo_coder.models import tool_1
# Create your views here.

class IndexView(TemplateView):
    template_name = 'agda/package-page.html'

    def get_context_data(self, *args, **kw):
        context = super(IndexView, self).get_context_data(**kw)
        return package_template_dict(self.request, app_package, *args, **kw)

class ToolView(FormView):
    template_name = 'species_geo_coder/speciesgeocoder.html'
    form_class    = SpeciesGeoCoderForm

    def form_valid(self, form):
        request = self.request

        ## These are all generic, should be extracted to a main class
        job = SpeciesGeoCoderJob(status=JOB_STATUS_LEVEL_ACCEPTED)
        job.save()
        job = SpeciesGeoCoderJob.objects.select_for_update().get(pk=job.id)
        job.log_create(request.user, 'Created in web interface.')

        verbose = form.cleaned_data['verbose']
        occurences = form.cleaned_data['occurences']
        plot = form.cleaned_data['plot']
        job.submit(request.user, request.META['REMOTE_ADDR'], form.cleaned_data['name'],
                self.request.FILES, occurences, verbose, plot)

        return redirect('jobs.views.show_results', job.slug)

def tool_1_results(request, slug):
    job = get_job_or_404(slug=slug, select_for_update=True)
    job.update_status(request.user)
    params = dict(job=job, tool=tool_1)
    return render(request, 'species_geo_coder/results.html', params)


#class ToolResultView(TemplateView):
#    template_name = '<app>/tool_result.html'
