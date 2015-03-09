from django.conf.urls import patterns

from jobs.models import Slug

urlpatterns = patterns('jobs.views',
    (r'^$', 'list_jobs'),
    (r'^delete/$', 'delete_jobs'),
    (r'^(%s)/$' % Slug.regex, 'show_results'),
    (r'^(%s)/delete/$' % Slug.regex, 'delete_job'),
    (r'^(%s)/rename/$' % Slug.regex, 'rename_job'),
    (r'^(%s)/take/$' % Slug.regex, 'take_job'),
)
