"""Development settings and globals."""

from .base import *  # noqa

PRODUCTION = False
########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION

try:
    TEMPLATE_DIRS += (
        '%s/lib/python2.7/site-packages/debug_toolbar/templates' % get_env_variable("VIRTUAL_ENV"),
    )
except ImproperlyConfigured:
    pass


########## TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INSTALLED_APPS += (
    'debug_toolbar',
    # 'django_extensions',
    # 'jobs',
)

## Important setting when running with wsgi
DEBUG_TOOLBAR_PATCH_SETTINGS = True

DEBUG_TOOLBAR_CONFIG = {
    #'INTERCEPT_REDIRECTS': False,
    #'MEDIA_URL': '/debug_toolbar_media/',
}

DEBUG_TOOLBAR_PANELS = (
    #'debug_toolbar.panels.version.VersionDebugPanel',
    #'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INTERNAL_IPS = ('127.0.0.1', '127.0.1.1', '10.211.55.2', '10.211.55.21')

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)
########## END TOOLBAR CONFIGURATION


########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s ((%(pathname)s:%(funcName)s)) %(message)s'
        },
        'simple': {
            'format': '[%(asctime)s] %(levelname)s %(message)s',
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'development': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': './agda.log',
            'level': 'INFO',
            'formatter': 'simple',
        }
    },
    'loggers': {
        '': {
            'handlers': ['development', 'file'],
            'level': 'INFO',
            'propagate': True
        },
        'agda': {
            'handlers': ['development'],
            'level': 'INFO',
            'propagate': True
        },
        'django.db.backends': {
            'handlers': ['development'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
########## END LOGGING CONFIGURATION
