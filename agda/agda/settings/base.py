"""Common settings and globals."""

import os
from sys import path
from os.path import abspath, basename, dirname, join, normpath

import ldap

# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django_auth_ldap.config import LDAPSearch, PosixGroupType
from django.core.exceptions import ImproperlyConfigured


def get_env_variable(var_name):
    """ Get the environment variable or return exception """
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the %s environment variable" % var_name
        raise ImproperlyConfigured(error_msg)


########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

PROJECT_ROOT = dirname(dirname(SITE_ROOT))

# Site name:
SITE_NAME = basename(DJANGO_ROOT)


# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
########## END PATH CONFIGURATION


########## LOGIN CONFIGURATION
# https://docs.djangoproject.com/en/1.6/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = '/login/'
########## END LOGIN CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('Jonas Hagberg', 'jonas.hagberg@bils.se'),
    ('Johan Viklund', 'johan.viklund@bils.se'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


SUPPORT_EMAIL = 'johan.viklund@bils.se'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


########## LDAP CONFIGURATION
AUTH_LDAP_START_TLS = True
AUTH_LDAP_GLOBAL_OPTIONS = {ldap.OPT_X_TLS_REQUIRE_CERT: False, }
AUTH_LDAP_SERVER_URI = get_env_variable("AGDA_AUTH_LDAP_SERVER_URI")
AUTH_LDAP_BIND_DN = get_env_variable("AGDA_AUTH_LDAP_BIND_DN")
AUTH_LDAP_BIND_PASSWORD = get_env_variable("AGDA_AUTH_LDAP_BIND_PASSWORD")

AUTH_LDAP_USER_SEARCH = LDAPSearch(
    "ou=users,dc=bils,dc=se",
    ldap.SCOPE_SUBTREE,
    "(uid=%(user)s)"
)

AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    "ou=System groups,ou=Groups,dc=bils,dc=se",
    ldap.SCOPE_SUBTREE,
    "(objectClass=PosixGroupType)"
)

AUTH_LDAP_GROUP_TYPE = PosixGroupType()
AUTH_LDAP_REQUIRE_GROUP = "cn=toolsportalUsers,ou=System groups,ou=Groups,dc=bils,dc=se"
########## END LDAP CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE':   '%s' % get_env_variable("AGDA_DB_ENGINE"),
        'NAME':     '%s' % get_env_variable("AGDA_DB_NAME"),
        'USER':     '%s' % get_env_variable("AGDA_DB_USER"),
        'PASSWORD': '%s' % get_env_variable("AGDA_DB_PASS"),
    }
}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'filesystem': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/agda/cache',
        'MAX_ENTRIES': 200000,
    },
}
########## END CACHE CONFIGURATION


########## AUTH CONFIGURATION
# Custom for Agda instead of separate profile.
AUTH_USER_MODEL = "profiles.AgdaUser"

# Authentication Backends
#AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',
#                           'agda.auth_backends.ClientCertificateBackend',
#                           )

AUTHENTICATION_BACKENDS = ('django_auth_ldap.backend.LDAPBackend',
                           'django.contrib.auth.backends.ModelBackend',
                           )
########## END AUTH CONFIGURATION


########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'Europe/Stockholm'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# Default Date and Time Formats
DATE_FORMAT = "Y-m-d"
DATETIME_FORMAT = "Y-m-d H:i:s"
TIME_FORMAT = "H:i:s"
########## END GENERAL CONFIGURATION

# Root of data files used by jobs:
DATA_ROOT = os.path.join(PROJECT_ROOT, 'db')
DATA_URL = '/data/'


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(PROJECT_ROOT, 'media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
########## END MEDIA CONFIGURATION


# Root directory for active grid jobs:
WORKDIR_ROOT = os.path.join(PROJECT_ROOT, 'work')

# Root directory and url for user-crated, non-django served files:
RESULTDIR_ROOT = os.path.join(MEDIA_ROOT, 'results')
RESULTDIR_URL = os.path.join(MEDIA_URL, 'results/')

# Root directory for failed grid jobs
ERRORDIR_ROOT = os.path.join(PROJECT_ROOT, 'failed')

# Settings for uploaded files that are cached server side until form is
# correctly filled out.
CACHED_UPLOAD_DIR = os.path.join(PROJECT_ROOT, 'upload')
CACHED_UPLOAD_VIEW = 'agda.views.review_cached_upload'

# We don't want execute permissions on uploaded stuff.
FILE_UPLOAD_PERMISSIONS = 0644


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, 'assets'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'static')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
########## END STATIC FILE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key should only be used for development and testing.
SECRET_KEY = get_env_variable("AGDA_SECRET_KEY")
AGDA_URL_BASE = get_env_variable("AGDA_URL_BASE")
AGDA_MAIL_FROM = get_env_variable("AGDA_MAIL_FROM")
AGDA_MAIL_WATCHERS = get_env_variable("AGDA_MAIL_WATCHERS")
AGDA_CONFIRMATION_MAIL_SECRET = get_env_variable("AGDA_CONFIRMATION_MAIL_SECRET")
########## END SECRET CONFIGURATION


########## SITE CONFIGURATION
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']
########## END SITE CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


API_PASSWORD_LENGTH = 20
API_PASSWORD_CHARACTERS = ('abcdefghjkmnpqrstuvwxyz'
                           'ABCDEFGHJKLMNPQRSTUVWXYZ'
                           '23456789'
                           '.,:;*+-_!#@%&/()[]{}=?<>')


########## TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    'agda.context_processors.site_settings',
    'agda.context_processors.user_profile',
    'agda.context_processors.job_status_levels',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
TEMPLATE_DIRS = (
    normpath(join(SITE_ROOT, 'templates')),
)
########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    # Default Django middleware.
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)
########## END MIDDLEWARE CONFIGURATION


########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION
DJANGO_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Useful template tags:
    # 'django.contrib.humanize',
    #  django admin theme
    'suit',
    # Admin panel and documentation:
    'django.contrib.admin',
    # 'django.contrib.admindocs',
)

THIRD_PARTY_APPS = (
    # Database migration helpers:
    'south',
    'django_extensions',
)

# Apps specific for this project go here.
LOCAL_APPS = (
    'agda',
    'profiles',
    'jobs',
    'mdr',
    'datisca',
    'pconsc',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
########## END APP CONFIGURATION


########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME
########## END WSGI CONFIGURATION
