import os
import sys
import site

# Add the site-packages of the chosen virtualenv to work with
site.addsitedir('/srv/virtual_env/agda-dev/lib/python2.6/site-packages/')

# Add the app's directory to the PYTHONPATH
sys.path.append('/srv/agda/agda-dev/agda')

# Activate your virtual env
activate_env=os.path.expanduser("/srv/virtual_env/agda-dev/bin/activate_this.py")
execfile(activate_env, dict(__file__=activate_env))

sys.path.insert(0, '/srv/virtual_env/agda-dev/')
sys.path.insert(1, '/srv/virtual_env/agda-dev/agda/')

os.environ['DJANGO_SETTINGS_MODULE'] = 'agda.settings.production'

_application = None

def application(environ, start_response):

    os.environ['GRIDMAPFILE_BASE'] = environ['GRIDMAPFILE_BASE']
    os.environ['AGDA_DB_ENGINE'] = environ['AGDA_DB_ENGINE']
    os.environ['AGDA_DB_NAME'] = environ['AGDA_DB_NAME']
    os.environ['AGDA_DB_USER'] = environ['AGDA_DB_USER']
    os.environ['AGDA_DB_PASS'] = environ['AGDA_DB_PASS']
    os.environ['AGDA_SECRET_KEY'] = environ['AGDA_SECRET_KEY']
    os.environ['AGDA_URL_BASE'] = environ['AGDA_URL_BASE']
    os.environ['AGDA_MAIL_FROM'] = environ['AGDA_MAIL_FROM']
    os.environ['AGDA_MAIL_WATCHERS'] = environ['AGDA_MAIL_WATCHERS']
    os.environ['AGDA_CONFIRMATION_MAIL_SECRET'] = environ['AGDA_CONFIRMATION_MAIL_SECRET']
    os.environ['VIRTUAL_ENV'] = environ['VIRTUAL_ENV']
    os.environ['AGDA_UTILS'] = environ['AGDA_UTILS']
    
    os.environ['AGDA_AUTH_LDAP_SERVER_URI'] = environ['AGDA_AUTH_LDAP_SERVER_URI']
    os.environ['AGDA_AUTH_LDAP_BIND_DN'] = environ['AGDA_AUTH_LDAP_BIND_DN']
    os.environ['AGDA_AUTH_LDAP_BIND_PASSWORD'] = environ['AGDA_AUTH_LDAP_BIND_PASSWORD']
    
    global _application
    
    if _application is None:
        from django.core.wsgi import get_wsgi_application
        _application = get_wsgi_application()
        
    return _application(environ, start_response)
