from functools import wraps
import json

from django.contrib.auth.models import (AnonymousUser,
                                        User,
                                        check_password)

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import mark_safe
from django.views.decorators.cache import never_cache

from forms.cached_uploads import review_cached_upload_view
from models import (api_get_available_tools,
                    get_available_packages,
                    get_available_tools,
                    )

### Authorization ###


def require_nothing(f):
    """Wrap the view function to require nothing."""
    @wraps(f)
    def wrapped_f(request, *args, **kwds):
        request.agda_authorization_checked = True
        return f(request, *args, **kwds)
    return wrapped_f


### Basic views ###

@never_cache
@require_nothing
def top(request):
    """
    Handle the top level (welcome) page.

    Django view.
    """
    return render(request, 'agda/top.html')


@never_cache
@require_nothing
def contact(request):
    """
    Handle the contact page.

    Django view.
    """
    return render(request, 'agda/contact.html')


@never_cache
@require_nothing
def new_user(request):
    """
    Handle the new user page.

    Django view.
    """
    return render(request, 'agda/new_user.html')


### HTTP BASIC AUTHENTICATION ###

def basic_challenge():
    """Basic http AUTH for API wrappers

    Returns
    -------

    HttpResponse : with WWW-Auth


    """
    response = HttpResponse('Please authenticate\n', mimetype="text/plain")
    response['WWW-Authenticate'] = 'Basic realm=API'
    response.status_code = 401
    return response


def get_basic_authorization(request):
    """Gets basic auth username and password

    Parameters
    ----------
    request : A django request obj

    Returns
    -------

    auth_username :   base64 decoded
    auth_password :   base64 decoded
    """
    http_auth = request.META.get('HTTP_AUTHORIZATION')

    if not http_auth:
        raise ValueError('http authorization missing')

    (auth_method, auth) = http_auth.split(None, 1)
    if auth_method.lower() != "basic":
        raise ValueError('bad http authorization method')

    try:
        auth_username, auth_password = auth.strip().decode('base64').split(':')
    except:
        raise ValueError('bad authorization encoding')

    return auth_username, auth_password


def get_basic_authenticated_api_user(request):
    """Get the agda user from basic auth
    Get the Agda user and profile from the basic http auth information.
    Checks the provided HTTP auth password against users profile API password

    Parameters
    ----------
    request : A django request obj

    Returns
    -------
    user : Authenticated Django agda user obj

    Raises
    ------
    ValueError()
       | If user has no profile.
       | If User has no api password set
       | If wrong api password
    """
    auth_username, auth_password = get_basic_authorization(request)

    try:
        user = User.objects.get(username=auth_username)
    except:
        raise ValueError('no such user')

    try:
        profile = user
    except:
        raise ValueError('user has no profile')

    if not profile.api_password or profile.api_password == '!':
        raise ValueError('user has no api password set')

    if not check_password(auth_password, profile.api_password):
        raise ValueError('wrong api password')

    # Authorized!
    return user


def api_require_nothing(f):
    """Wrap the api view function to require nothing.

    Decorated to exempt the Cross Site Request Forgery protection
    It is needed to exempt the csrf for the api functions.
    """
    @wraps(f)
    @csrf_exempt
    def wrapped_f(request, *args, **kwds):
        try:
            api_user = get_basic_authenticated_api_user(request)
        except:
            if request.META.get('HTTP_AUTHORIZATION'):
                return basic_challenge()
            api_user = AnonymousUser()
        request.agda_api_user = api_user
        request.agda_authorization_checked = True
        return f(request, *args, **kwds)
    return wrapped_f


### Helpers ###

def package_template_dict(request, package, *args, **kw):
    """Context vars suitable for templates that extend package-page.

    see datisca/templates/top.html


    See also
    --------
    models.package.get_available_tools
    models.tools.available
    """
    available_tools = package.get_available_tools(request.user)
    return dict(*args, package=package, package_tools=available_tools, **kw)


def json_datetime_encoder(obj):
    """Use as a json.dump default= function to encode datetimes as isoformat strings."""
    try:
        return obj.isoformat()
    except:
        raise TypeError('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))


def json_response(data, status=200, default=None):
    """JSON-encode basic python data data and return it in a response.

    default is passed to json.dumps, and should be a callable such that
    default(obj) should return something that is json serializable.
    """
    body = json.dumps(data, default=default)
    return HttpResponse(body, mimetype='application/json', status=status)


def script_data(data):
    """json dumps data and use Django utils mark_safe to
     Explicitly mark a string as safe for (HTML) output purposes
     """
    return mark_safe(json.dumps(data))


def stream(*parts):
    for part in parts:
        if isinstance(part, basestring):
            part = [part]
        for text in part:
            yield text


def render_and_split(template, split, dictionary=None, context=None, split_tag='SPLIT_RENDERED_TEMPLATE_HERE'):
    params = dict.fromkeys(split, split_tag)
    params.update(dictionary)
    return render_to_string(template, params, context_instance=context).split(split_tag)


review_cached_upload = require_nothing(review_cached_upload_view)


### Tools ###

@api_require_nothing
def api_list_tools(request):
    services = dict()
    for tool in api_get_available_tools(request.agda_api_user):
        services[tool.name] = request.build_absolute_uri(reverse(tool.api_view))
    return json_response(services)


@require_nothing
def list_tools(request):
    available = get_available_tools(request.user)
    available.sort(key=lambda tool: tool.nickname.lower())
    return render(request, 'agda/list-tools.html', dict(tools=available))


@require_nothing
def list_packages(request):
    available = get_available_packages(request.user)
    available.sort(key=lambda package: package.nickname.lower())
    return render(request, 'agda/list-packages.html', dict(packages=available))
