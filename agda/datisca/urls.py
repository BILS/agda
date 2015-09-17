from django.conf.urls import patterns

urlpatterns = patterns('datisca.views',
    (r'^datisca/$', 'top'),
    (r'^datisca/nodule/$', 'nodule_trans_blast'),

    (r'^api/datisca/nodule/$', 'api_nodule_trans_blast'),
)
