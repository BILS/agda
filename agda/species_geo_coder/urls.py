from django.conf.urls import patterns, url

from .views import IndexView, ToolView

urlpatterns = patterns('',
    url(r'^/?$', IndexView.as_view(), name='species_geo_coder.views.top'),
    url(r'^/help/?$', IndexView.as_view(), name='species_geo_coder.views.top'),
    url(r'^/tool/?$', ToolView.as_view(), name='species_geo_coder.views.tool_1'),
)
