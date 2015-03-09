from django.conf.urls import patterns, include, url

from jobs.models import Slug

urlpatterns = patterns('jobs.views_api',
    (r'^$', 'api_list_jobs'),
    (r'^delete/$', 'api_delete_jobs'),
    (r'^(%s)/$' % Slug.regex, 'api_show_results'),
    (r'^(%s)/delete/$' % Slug.regex, 'api_delete_job'),
    (r'^(%s)/rename/$' % Slug.regex, 'api_rename_job'),
    (r'^(%s)/take/$' % Slug.regex, 'api_take_job'),
)
