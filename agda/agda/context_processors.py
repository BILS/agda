from django.contrib.auth.models import AnonymousUser
from django.conf import settings

from jobs.models import job_status_levels as job_states


# Export the setting(s) we need access to in templates
def site_settings(request):
    return dict(DATA_URL=settings.DATA_URL,
                PRODUCTION=settings.PRODUCTION,
                SITE_NAME=settings.SITE_NAME,
                support_email=settings.SUPPORT_EMAIL
                )


# Export user and profile for access in templates
def user_profile(request):
    user = request.user
    profile = None
    if not isinstance(user, AnonymousUser):
        profile = user
    return dict(user=user, profile=profile)


class CaseInsensitiveDict(dict):
    def __getitem__(self, key):
        if isinstance(key, basestring):
            key = key.lower()
        return super(CaseInsensitiveDict, self).__getitem__(key)

    def __setitem__(self, key, value):
        if isinstance(key, basestring):
            key = key.lower()
        return super(CaseInsensitiveDict, self).__setitem__(key, value)


def job_status_levels(request):
    """Case insensitive job status level lookup in templates."""
    lookup = CaseInsensitiveDict(job_states)
    for state_code, name in job_states.items():
        if isinstance(name, basestring):
            lookup[name.lower()] = state_code
    return dict(job_status=lookup)
