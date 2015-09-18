from django.conf.urls import patterns

urlpatterns = patterns('pconsc.views',
    (r'^pconsc/$', 'top'),
    (r'^pconsc/predictall/$', 'predictall'),

    (r'^api/pconsc/predictall/$', 'api_predictall'),
)
