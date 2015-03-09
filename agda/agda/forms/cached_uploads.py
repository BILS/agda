"""
Helpers to get ClearableFileInput to behave as advertised.

CachedUpload is what's needed by the ClearableFileInput widget in order for it
to display the "clear" checkbox.

manage_clearable_file_input*() manages request.FILES and form initial data,
but takes no responsibility for persistence.

get/store/clear_cached_uploads() takes care of persistence using session
variables and NamedTemporaryFiles.

review_cached_upload_view() is a view function that makes sure users only view
*their* uploads, and not anybody else's, and certainly not arbitrary files from
the file system, and only as an attachment, and not as something IE5 should try
to run VB scripts out of. Also it's streamed.

intended use:

.. code-block:: python

 def my_view(request)
    key_base = 'form_unique.dotted.if_needed'
    filefield_names = ['sequence']
    cached_uploads = CachedUploadManager.get_from_session(request.session,
        key_base, filefield_names)
    ok_to_save, form = get_form(MyForm, request, initial=cached_uploads)
    cached_uploads.manage_inputs(request, form)
    # Do any additional validation
    # Set cached_uploads[key] = None for bad uploads you want to get rid of.
    if ok_to_save:
        # Do fancy and incredible stuff, then clear the cached uploads.
        # This clears them from both session and file system.
        cached_uploads.clear_from_session()
    else:
        # Store the good uploads, drop the bad, (re-)display the form.
        cached_uploads.store_in_session()
    form.initial.update(cached_uploads)
    return render(request, 'my_view.html', dict(form=form))

or:

.. code-block:: python

 def my_view(request)
    key_base = 'form_unique.dotted.if_needed'
    filefield_names = ['sequence']
    cached_uploads = get_cached_uploads(request.session, key_base,
        filefield_names)
    ok_to_save, form = get_form(MyForm, request, initial=cached_uploads)
    cached_uploads = manage_clearable_file_inputs(request, form,
        cached_uploads)
    # Do any additional validation
    # Set cached_uploads[key] = None for bad uploads you want to get rid of.
    if ok_to_save:
        # Do fancy and incredible stuff, then clear the cached uploads.
        # This clears them from both session and file system.
        clear_cached_uploads(request.session, key_base, cached_uploads)
    else:
        # Store the good uploads, drop the bad, (re-)display the form.
        store_cached_uploads(request.session, key_base, cached_uploads)
    form.initial.update(cached_uploads)
    return render(request, 'my_view.html', dict(form=form))
"""

import os
from tempfile import NamedTemporaryFile

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404


def review_cached_upload_view(request, slug):
    """
    View function that serves cached uploads securely and efficiently.

    This view serves uploaded files:

    * and uploaded files only (not arbitrary files from the server).
    * to the uploader only (determined by session specific variable).
    * as an attachment (so IE will not run VB scripts out of it).
    * streamed (file is not read all into memory before returning it).
    """
    expected = CachedUpload.get_path(slug)
    for key, value in request.session.items():
        if getattr(value, 'slug', None) == slug and value.path == expected:
            f = open(expected)
            response = HttpResponse(f, content_type=value.content_type)
            response['Content-Disposition'] = \
                'attachment; filename=' + value.name
            response['Content-Length'] = str(os.path.getsize(expected))
            return response
    raise Http404


class CachedUpload(object):
    """
    A helper to get ClearableFileInput to behave as advertised.

    A CachedUpload is an uploaded file that is cached server side until a
    form is correctly filled in. It has a .url attribute which is required
    by ClearableFileInput in form initial data in order to display the "clear"
    widget.
    """
    dir = getattr(settings, 'CACHED_UPLOAD_DIR', settings.FILE_UPLOAD_TEMP_DIR)
    view = getattr(settings, 'CACHED_UPLOAD_VIEW', 'review_cached_upload')

    suffix = '.upload'

    def __init__(self, name=None, slug=None, content_type='text/plain',
                 uploaded_file=None):
        self.name = name
        self.slug = slug
        self.content_type = type
        self.uploaded_file = uploaded_file

    def __eq__(self, other):
        return (self.slug == other.slug and
                self.uploaded_file == other.uploaded_file,
                self.name == other.name and
                self.content_type == other.content_type)

    @classmethod
    def wrap(cls, uploaded_file):
        return cls(uploaded_file=uploaded_file)

    def __repr__(self):
        l = super(CachedUpload, self).__repr__().split(None, 1)
        if self.name:
            l.insert(1, self.name)
        return ' '.join(l)

    def __unicode__(self):
        return unicode(self.name)

    @classmethod
    def get_path(cls, slug):
        name = slug + cls.suffix
        return os.path.join(cls.dir, name)

    url = property(lambda self: reverse(self.view, args=[self.slug]))
    path = property(lambda self: self.get_path(self.slug))

    def exists(self):
        return bool(self.slug) and os.path.exists(self.path)

    def remove(self):
        if self.exists():
            os.remove(self.path)

    def save(self):
        tempfile = NamedTemporaryFile(
            dir=self.dir,
            prefix='',
            suffix=self.suffix,
            delete=False
        )
        tempfile.writelines(line for line in self.uploaded_file)
        tempfile.close()
        self.name = self.uploaded_file.name
        # The 6 random chars generated by NamedTemporaryFile is a good slug.
        self.slug = os.path.split(tempfile.name)[1][:6]
        self.content_type = self.uploaded_file.content_type
        self.uploaded_file = None

    def open(self):
        f = self.uploaded_file or open(self.path)
        f.seek(0)
        return f

    def contents(self):
        return self.open().read()


def manage_clearable_file_input(request, form, field_name):
    """
    Manage the request.FILES and form initial data for a ClearableFileInput.

    Wraps an uploaded file (if any) in a CachedUpload, and sets request.FILES
    and form initial data so that the ClearableFileInput can work as
    advertised.

    This function determines data cleanness from form.errors[field_name]. Any
    other errors (e.g. non_field_errors or errors caught at the view level)
    must be manually managed.

    Ensuring persistence between requests is the responsibility of the caller.
    The CachedUpload object (or None) will be returned as a convenience for
    this purpose.

    Any previous CachedUpload must be present as form initial data.
    """
    new_upload = form.fields[field_name].widget.value_from_datadict(
        request.POST,
        request.FILES,
        field_name
    )
    cached_upload = form.initial.get(field_name)
    if new_upload is None or \
       new_upload is forms.widgets.FILE_INPUT_CONTRADICTION:
        # We should keep an eventual previous upload.
        return cached_upload
    if form.errors.get(field_name, None):
        # Unclean data should not be cached.
        return None
    # An eventual previous upload should be cleared.
    if cached_upload:
        cached_upload.remove()
        cached_upload = None
    if new_upload:
        # new_upload is not False: there is new content.
        cached_upload = CachedUpload(uploaded_file=new_upload)
    form.initial[field_name] = cached_upload
    request.FILES[field_name] = None
    return cached_upload


def manage_clearable_file_inputs(request, form, field_names):
    """
    Call manage_clearable_file_input for all given fields and return a dict
    with the results.
    """
    cached_uploads = dict()
    for field_name in field_names:
        cached_uploads[field_name] = manage_clearable_file_input(
            request,
            form,
            field_name
        )
    return cached_uploads


def store_cached_uploads(session, key_base, cached_uploads):
    """
    Save CachedUploads and store them as form specific session variables.

    Useful for saving data from get_cached_uploads and
    manage_clearable_file_inputs.

    Session variables will be stored as session[key_base + '.' + key] = value.
    Ensure key uniqueness, for example by using a hierarchical dotted form with
    tool name as base.

    Nonexisting items are deleted from the session.
    """
    for field_name, cached_upload in cached_uploads.items():
        key = key_base + '.' + field_name
        if cached_upload:
            if cached_upload.uploaded_file:
                cached_upload.save()
            if session.get(key, None) != cached_upload:
                session[key] = cached_upload
        else:
            session.pop(key, None)


def clear_cached_uploads(session, key_base, cached_uploads):
    """
    Remove CachedUploads from session and file system.

    Useful for clearing data set by store_cached_uploads.
    """
    for field_name, cached_upload in cached_uploads.items():
        key = key_base + '.' + field_name
        if cached_upload and cached_upload.exists():
            cached_upload.remove()
        session.pop(key, None)


def get_cached_uploads(session, key_base, field_names):
    """
    Get a dict of CachedUploads from the session, usable as form initial data.

    Useful for retrieving data set by store_cached_uploads.

    Nonexisting items are deleted from the session and returned as None.
    """
    cached_uploads = dict()
    for field_name in field_names:
        key = key_base + '.' + field_name
        cached_upload = session.get(key, None)
        if not cached_upload or not cached_upload.exists():
            session.pop(key, None)
        cached_uploads[field_name] = cached_upload
    return cached_uploads


class CachedUploadManager(dict):
    """
    A dict with a tiny bit of extra sugar to manage a set of CachedUploads in a
    view.
    """

    def __init__(self, session=None, key_base=None, *args, **kw):
        super(CachedUploadManager, self).__init__(*args, **kw)
        self.session = session
        self.key_base = key_base

    @classmethod
    def get_from_session(cls, session, key_base, field_names):
        ret = cls(session, key_base)
        ret.update(get_cached_uploads(session, key_base, field_names))
        return ret

    def manage_inputs(self, request, form):
        """
        Updates self, request.FILES and form initial data so that
        ClearableFileInputs work.
        """
        self.update(**manage_clearable_file_inputs(request, form, self.keys()))

    def clear_from_session(self):
        clear_cached_uploads(self.session, self.key_base, self)

    def store_in_session(self):
        store_cached_uploads(self.session, self.key_base, self)
