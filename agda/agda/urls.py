from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('agda.views',
    url(r'^$', 'top'),
    url(r'^contact$', 'contact'),
    url(r'^new_user$', 'new_user'),
    url(r'^admin/', include(admin.site.urls)),

    (r'^review_cached_upload/tmp([A-Za-z0-9_]{6})/$', 'review_cached_upload'),

    (r'^packages/$', 'list_packages'),
    (r'^tools/$', 'list_tools'),

    (r'^api/$', 'api_list_tools'),
    (r'^api/tools/$', 'api_list_tools'),
)

### Plugins ###

urlpatterns += patterns('',
    ('^results/', include('jobs.urls')),
    ('^api/results/', include('jobs.urls_api')),
    ('', include('profiles.urls')),
    ('', include('mdr.urls')),
)
