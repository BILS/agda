import logging

from django.views.generic import UpdateView
from braces.views import LoginRequiredMixin

from django import forms
from django.conf import settings
from django.contrib import (auth,
                            messages)
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from django.core.exceptions import ValidationError
from django.shortcuts import (redirect,
                              render)
from django.utils.html import mark_safe
from django.views.decorators.cache import never_cache

from agda.forms import (change_message_from_form,
                        get_form)

from agda.utils import (ModelDiffer,
                        get_initial)
from agda.views import (top,
                        require_nothing)


from .models import (AgdaUser,
                     email_max_length)

from .forms import AgdaUserEditForm

from profiles.utils import get_cracklib_complaints

logger = logging.getLogger(__name__)


class AgdaUserUpdateView(LoginRequiredMixin, UpdateView):
    # model=AgdaUser
    form_class = AgdaUserEditForm

    def get_object(self):
        return AgdaUser.objects.get(username=self.request.user)


### Login and logout ###
@never_cache
@require_nothing
def login(request):
    """Handle login."""
    login_successful, form = get_form(LoginForm, request)
    if login_successful:
        messages.success(request, "You are now logged in.")
        return login_success(request, form.cleaned_data['user'], form.cleaned_data['profile'], "password")
    return render(request, 'profiles/login.html', dict(form=form, next=request.GET.get('next', '')))


def login_success(request, user, profile, login_method):
    auth.login(request, user)
    logger.info("%s: logged in using %s (%s)" %
            (user.email, login_method, request.session['_auth_user_backend']))
    redirect_target = request.POST.get('next', 'agda.views.top')
    if redirect_target == '':
        redirect_target = 'agda.views.top'
    response = redirect(redirect_target)
    # Remember how we logged in, and that we are now no longer redirected for logging in
    response.set_cookie("last_login_type", login_method, max_age=365 * 24 * 60 * 60)
    request.session['redirected_to_login'] = False
    return response


@never_cache
@require_nothing
def logout(request):
    """Handle logout."""
    logger.info("%s: logged out." % (request.user.email))
    auth.logout(request)
    messages.success(request, "You are now logged out.")
    return redirect('agda.views.top')


class LoginForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=email_max_length)
    password = forms.CharField(max_length=email_max_length, widget=forms.PasswordInput(render_value=True))

    def clean(self):
        """Populates cleaned data dict with user and profile on login success."""
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        if not email and password:
            return
        user = auth.authenticate(username=email, password=password)
        if user and user.is_active:
            try:
                profile = user
                if profile:
                    # This is the only code path to login success.
                    self.cleaned_data.update(user=user, profile=profile)
                    return self.cleaned_data
                else:
                    self._errors.setdefault('__all__', []).append('This user is not authorized.')
                    logger.warn("%s: tried to login but is not authorized." % email)
            except profile.DoesNotExist:
                self._errors.setdefault('__all__', []).append('This user has no profile.')
                logger.warn("%s: tried to login but is not connected to a profile." % email)
        else:
            self._errors.setdefault('__all__', []).append('Invalid username or password.')
            logger.warn("%s: failed to login." % email)
        # At this point login has failed and we return None.
        return None


### Account management ###
def clean_email(form):
    value = form.cleaned_data['email']
    if value == form.initial.get('email'):
        raise ValidationError('It is the same as the old address.')
    if User.objects.filter(email=value).count() != 0:
        msg = mark_safe('The email address is already in use: '
                        '<a href="%s" class="important">Get access to your existing account</a>')
        raise ValidationError(msg)
    return value


def form_clean_password(form):
        if form.cleaned_data.get("password1", ""):
            if form.cleaned_data.get("password1", "") != form.cleaned_data.get("password2", ""):
                for i in (1, 2):
                    form._errors.setdefault('password%d' % i, []).append("Passwords do not match.")
            else:
                complaints = get_cracklib_complaints(form.cleaned_data.get("password1", ""))
                if complaints:
                    form._errors.setdefault('password1', []).append("Bad password: %s." % complaints)
        return form.cleaned_data


class AccountChangeEmailForm(forms.Form):
    email = forms.EmailField(max_length=email_max_length)

    def clean_email(self):
        return clean_email(self)


class AccountNewPasswordForm(forms.Form):
    # Max password length same as User.email max_length
    password1 = forms.CharField(max_length=email_max_length, widget=forms.PasswordInput(render_value=True), label="New Password")
    password2 = forms.CharField(max_length=email_max_length, widget=forms.PasswordInput(render_value=True), label="New Password (again)")

    def clean(self):
        return form_clean_password(self)


class AccountChangeBasicInformationForm(forms.Form):
    # Name max length same as User.*_name max_length
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)


class AccountCreateForm(forms.Form):
    email = forms.EmailField(max_length=email_max_length)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    password1 = forms.CharField(max_length=email_max_length, widget=forms.PasswordInput(render_value=True), label="Password")
    password2 = forms.CharField(max_length=email_max_length, widget=forms.PasswordInput(render_value=True), label="Password (again)")

    annotations = dict(
        comments=dict(email='This will also be your Agda username. You will have to confirm this address by following a link in an email sent to it.')
        )

    def clean_email(self):
        return clean_email(self)

    def clean(self):
        return form_clean_password(self)


@never_cache
@login_required
def account_change_email(request):
    user = request.user
    profile = user
    ok_to_save, form = get_form(AccountChangeEmailForm, request)
    if not ok_to_save:
        if not form.initial:
            email = user.email
            form.initial['email'] = email
        return render(request, 'agda/account/change_email.html', dict(form=form))
    profile.save()
    profile.log_change(request.user, message="Agda: email change to %s requested" % profile.email)
    profile.send_email("Confirm your Agda email address change",
                       "agda/account/confirm_change_email.txt",
                       use_email_pending=True)
    if user.email:
        profile.send_email("Information about Agda email address change",
                           "agda/account/inform_change_email.txt",
                           use_email_pending=False)
    msg = "You have requested an email address change. Confirmation email sent to new address <b>%(new)s</b>"
    if user.email:
        msg += " Notification email sent to old address <b>%(old)s</b>"
    msg += '.'
    messages.info(request, mark_safe(msg % dict(old=user.email, new=profile.email)))
    return redirect(top)


@never_cache
def account_confirm_email(request, profile_id, confirmation_code):
    """Handle email address confirmation URL."""
    user = request.user
    profile = user
    if profile.valid:
        return render(request, 'agda/account/confirm_email.html')

    # Check if the confirmation code works
    code_ok = profile.check_email_confirmation_code(confirmation_code)

    # Check that this email_pending is not the confirmed email of another User
    users = User.objects.filter(username=profile.email)
    if users and (len(users) > 1 or users[0] != profile):
        code_ok = False

    if code_ok and request.POST.get("confirmed"):
        # Register the email as confirmed, and the account therefore as valid.
        user.username = profile.email
        user.save()
        profile.save()
        profile.log_change(profile, message="Agda: Email %s confirmed, user level now %s." % (user.username))
        profile.send_email("%s %s: Agda account created" % (user.first_name, user.last_name),
                           "agda/account/validated_email.txt",
                           cc_recipients=[settings.AGDA_MAIL_WATCHERS])
        # Redirect with message
        messages.success(request, "Your email address has now been confirmed.")
        return redirect(top)

    logger.warn("Failed email confirmation for profile %s." % profile)
    return render(request, 'agda/account/confirm_email.html', dict(code_ok=code_ok, confirmed=False))


class AccountChangePasswordForm(forms.Form):
    # Max password length same as User.email max_length
    old_password = forms.CharField(max_length=email_max_length, widget=forms.PasswordInput(render_value=True), label="Old Password")
    password1 = forms.CharField(max_length=email_max_length, widget=forms.PasswordInput(render_value=True), label="New Password")
    password2 = forms.CharField(max_length=email_max_length, widget=forms.PasswordInput(render_value=True), label="New Password (again)")

    def __init__(self, *args, **kw):
        self.user = kw.pop('user', None)
        super(AccountChangePasswordForm, self).__init__(*args, **kw)

    def clean_old_passsword(self):
        if not self.user.check_password(self.cleaned_data.get('old_password', '')):
            self._errors.setdefault('old_password', []).append('Not correct.')

    def clean(self):
        return form_clean_password(self)


@never_cache
@login_required
def account_change_password(request):
    user = request.user
    ok_to_save, form = get_form(AccountChangePasswordForm, request, user=user)
    if not ok_to_save:
        return render(request, 'agda/account/change_password.html', dict(form=form))
    # OK to save.
    user.set_password(form.cleaned_data["password1"])
    user.save()
    user.log_change(user, "Changed own password.")
    messages.success(request, "Your password has been changed.")
    return redirect(account_edit)


class AccountEditForm(AccountChangeBasicInformationForm):
    pass


@never_cache
@login_required
def account_edit(request):
    """Edit account information."""
    user = request.user
    profile = user

    ok_to_save, form = get_form(AccountEditForm, request)
    if not ok_to_save:
        # Redisplay or present empty form
        form.initial = get_initial(user, form)
        return render(request, 'agda/account/edit.html', dict(form=form))
    # OK to save.
    md = ModelDiffer(user)
    for field in form.fields:
        setattr(user, field, form.cleaned_data[field])
    user.save()
    md.update(user)
    profile.log_change(user, message="Agda: " + change_message_from_form(form))
    profile.send_email("%s %s: Agda account information updated" % (user.first_name, user.last_name),
                       "agda/account/changed_email.txt",
                       extra_dict=dict(change_report=md.get_change_report()),
                       cc_recipients=[settings.AGDA_MAIL_WATCHERS])
    messages.success(request, "Your account information has been saved.")
    return redirect(top)


@never_cache
@login_required
def account_api_password_reset(request):
    """Reset the user's api password."""
    if request.method != 'POST':
        return render(request, 'agda/account/api_password_reset.html')
    profile = request.user
    modified = profile.has_usable_api_password()
    api_password = User.objects.make_random_password(settings.API_PASSWORD_LENGTH, settings.API_PASSWORD_CHARACTERS)
    profile.set_api_password(api_password)
    profile.save()
    profile.log_change(request.user, "Generated new api password.")
    return render(request, 'agda/account/api_password_reset.html', dict(api_password=api_password, modified=modified))


@never_cache
@login_required
def account_api_password_disable(request):
    """Delete the user's api password."""
    if request.method != 'POST':
        return render(request, 'agda/account/api_password_disable.html')
    profile = request.user
    profile.set_api_password(None)
    profile.save()
    profile.log_change(request.user, "Deleted own api password.")
    messages.success(request, "Your api password has been disabled.")
    return redirect(account_edit)
