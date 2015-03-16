from django.conf.urls import patterns

urlpatterns = patterns('mdr.views',
    (r'^mdr/$', 'top'),
    (r'^mdr/scan/$', 'scan'),
    (r'^mdr/search/$', 'search'),
    (r'^mdr/family/$', 'family_lookup'),
    (r'^mdr/family/(\w*)$', 'family_lookup'),

    (r'^api/mdr/scan/$', 'api_scan'),
    (r'^api/mdr/search/$', 'api_search'),
    (r'^api/mdr/family/$', 'api_family_lookup'),
)
