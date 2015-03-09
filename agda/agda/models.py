import logging

from django.contrib.admin.models import (ADDITION,
                                         CHANGE,
                                         DELETION,
                                         LogEntry)

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.encoding import force_unicode
from django.utils.text import get_text_list

logger = logging.getLogger(__name__)


class AgdaModelMixin:
    @classmethod
    def search(Model, key, manager=None):
        """Search for objects matching the specified key.

        Returns
        -------
        QuerySet : Override this in the concrete models
        to do a search relevant for that model.
        """
        if manager is None:
            manager = Model.objects
        return manager.none()

    def ok_to_delete(self):
        """Is it OK to delete this object?

        Returns
        -------
        Boolean : True only if it is safe to delete this object, taking
        into account Django's cascading delete. Override this in the
        concrete models.
        """
        return False

    def get_model_verbose_name(self):
        """
        Returns
        -------
        the verbose name (without spaces).
        """
        return self._meta.verbose_name.replace(" ", "")

    @classmethod
    def cls_get_model_verbose_name(cls):
        """
        Returns
        -------
        the verbose name (without spaces).
        """
        return cls._meta.verbose_name.replace(" ", "")

    def change_message_for_fields(self, fields, valueless=[]):
        out = ["Changed %s to '%s'." % (name, unicode(getattr(self, name))) for name in fields]
        if valueless:
            out.append('Changed %s.' % get_text_list(valueless, 'and'))
        return ' '.join(out)

    def log_action(self, action_flag, user, message, object_repr):
        le = LogEntry(user_id=user.pk,
                      content_type_id=ContentType.objects.get_for_model(self).pk,
                      object_id=self.pk,
                      object_repr=object_repr,
                      action_flag=action_flag,
                      change_message=message,
                      )
        le.save()
        action = {
            ADDITION: "Created",
            CHANGE: "Changed",
            DELETION: "Deleted"
        }.get(action_flag, "?")
        message = force_unicode(message)
        logger.info(u"%s:  %s %s %s - %s" % (user.email,
                                             action,
                                             self._meta.verbose_name,
                                             object_repr,
                                             message))

    def log_create(self, user, message=""):
        self.log_action(ADDITION,
                        user,
                        message,
                        force_unicode(self),
                        )

    def log_change(self, user, message=""):
        self.log_action(CHANGE,
                        user,
                        message,
                        force_unicode(self),
                        )

    def log_delete(self, user, object_repr, message=""):
        self.log_action(DELETION,
                        user,
                        message,
                        object_repr,
                        )

    def get_current(self):
        return self.__class__.objects.get(pk=self.pk)


# Tools and packages #

_packages = dict()
_tools = dict()


def register_tool(tool):
    """
    Registers the tool with the internal tool dictionary.
    """
    if tool.name in _tools:
        return
    if tool.name in _packages:
        raise ValueError('already registered as package')
    if tool.package:
        tool.package.add_tool(tool)
    _tools[tool.name] = tool


def register_package(package):
    """
    Registers the package with the internal package dictionary.
    """
    if package.name in _packages:
        return
    if package.name in _tools:
        raise ValueError('already registered as tool')
    _packages[package.name] = package


def get_available_packages(user):
    return [p for p in _packages.values() if p.available(user)]


def get_available_tools(user):
    return [t for t in _tools.values() if t.available(user)]


def api_get_available_tools(user):
    return [t for t in _tools.values() if t.api_available(user)]


class Tool(object):
    """
    A tool is a specific job to run. Tools should be owned by a Package.
    """
    def __init__(self, name, nickname, description, css_name=None, view=None,
                 api_view=None, package=None, results_view=None,
                 api_results_view=None):
        if css_name is None:
            css_name = name.replace('/', '-')
        self.name = name
        self.css_name = css_name
        self.nickname = nickname
        self.description = description
        self.view = view
        self.results_view = results_view
        self.api_view = api_view
        self.api_results_view = api_results_view
        self.package = package

    def register(self):
        """
        Calls register_tool(self) to register the tool with the internal
        tool registry
        """
        register_tool(self)

    def url(self):
        """Returns the URL for the tool. For use in templates"""
        return reverse(self.view, None)

    def results_url(self, slug):
        """Returns the URL for the result view."""
        return reverse(self.results_view, args=[slug])

    def available(self, user):
        """
        Checks whether the tool is available to the user.

        Returns
        -------
        Boolean : True only if tool has a view and if the user has access to
        the associated package.
        """
        if self.package:
            return bool(self.view and self.package.available(user))
        return self.view

    def api_available(self, user):
        """
        Checks whether the api interface is available for the specific user.

        Returns
        -------
        Boolean : True only if tool has an api_view and if the user has access
        to the associated package.
        """
        if self.package:
            return bool(self.api_view and self.package.available(user))
        return self.api_view


class Package(object):
    """
    A package is a collection of tools. Usually it's just a django app.
    """
    def __init__(self, view=None, name=None, nickname=None, description=None,
                 css_name=None, tools=None, permission=None):
        if tools is None:
            tools = []
        self._tools = tools
        if css_name is None:
            css_name = name.replace('/', '-')
        self.css_name = css_name
        self.view = view
        self.name = name
        self.nickname = nickname
        self.description = description
        self.permission = permission

    def register(self):
        """
        Calls register_package(self) to registers the package with the
        internal package registry

        Returns
        -------
        Package : Self
        """
        register_package(self)
        return self

    def url(self):
        """Returns the URL for the package. For use in templates"""
        return reverse(self.view, None, None)

    def add_tool(self, tool):
        """
        Add a tool to the package. Also registers the tool with the tool
        registry and updates the tool to have this package as it's owner.

        Important: The tool must have tool.package == None
        """
        tool.register()
        if tool.name not in self._tools:
            tool.package = self
            self._tools.append(tool)

    def new_tool(self, **kw):
        """
        Create a new tool. All parameters will be taken as arguments to the
        Tool constructor. This also runs add_tool.

        Returns
        -------
        Tool : The new tool
        """
        tool = Tool(**kw)
        self.add_tool(tool)
        return tool

    def available(self, user):
        """
        Checks whether the package is available to the user.

        Returns
        -------
        Boolean : True only if package has a view and, if the package has
        a set permission, if the user has that permission.
        """
        if self.permission:
            return bool(self.view and user.has_perm(self.permission))
        return bool(self.view)

    def get_available_tools(self, user):
        """
        Get all available tools

        Returns
        -------
        List : All tools if the user satisfies package.available(user).
        """
        if self.available(user):
            return list(self._tools)
        return list()

    def api_get_available_tools(self, user):
        """
        Get all tools that the user has api access to.

        Currently unimplemented
        """
        pass
        # return [t for t in self._tools if t.api_available(user)]
