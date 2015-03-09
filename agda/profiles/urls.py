from django.conf.urls import patterns

from .views import AgdaUserUpdateView


urlpatterns = patterns("profiles.views",
    (r'^edit/$', AgdaUserUpdateView.as_view()),
    (r'^login/$', 'login'),
    (r'^logout/$', 'logout'),

    (r'^account/change_email/$', 'account_change_email'),
    (r'^account/change_password/$', 'account_change_password'),
    # we use a shorter URL for the confirmation so we can fit it into the email on one line
    (r'^confirm/([0-9]+)/([0-9a-fA-F]+)/$', 'account_confirm_email'),
    (r'^account/edit/$', 'account_edit'),

    (r'^account/api_password/disable/$', 'account_api_password_disable'),
    (r'^account/api_password/reset/$', 'account_api_password_reset'),
    (r'^account/api_password/disable/$', 'account_api_password_disable'),
    )
