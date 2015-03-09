import string
import re

from django.db import models

from django.contrib.auth.models import (BaseUserManager,
                                        AbstractBaseUser,
                                        PermissionsMixin)

from django.contrib.auth import get_user_model
from django.contrib.auth.models import (check_password,
                                        is_password_usable,
                                        make_password)
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string

from agda.models import AgdaModelMixin

from agda.settings.local import (AGDA_MAIL_FROM,
                                 AGDA_URL_BASE)
from agda.utils import asciify


def get_system_user():
    """This method is used by the API.

    Returns
    -------
    user : user object where user name is 'system'
    """
    try:
        return get_user_model().objects.get(email='system@agda-devel')
    except:
        user = get_user_model()(username='system@agda-devel')
        user.set_unusable_password()
        user.save()
        return user


def get_anonymous_user():
    """Group account for anonymous users.

    |All anonymous job submissions are made through this user. This user only exists so that anonymous jobs can be logged through normal procedures,which requires a properly stored django auth.User.

    |Note : Job.user should be left blank for anonymous jobs, and should never be set to this user.

    Returns
    -------
    user : user object where user name is 'anonymous'
    """
    try:
        return get_user_model().objects.get(email='anonymous@agda-devel')
    except:
        user = get_user_model()(email='anonymous@agda-devel')
        user.set_unusable_password()
        user.save()
        return user


def get_user_or_anonymous(user):
    """Convenience for logging anonymous jobs.

    Returns
    -------
    user : if user is authenticated returns user
           else returns anonymous user
    """
    if user.is_authenticated():
        return user
    return get_anonymous_user()


### Users and profiles ###

def sanitize_name_for_login(name):
    res = asciify(name.lower())
    # If we haven't mapped a character to [a-z], get rid of it
    res = re.sub(r'[^a-z]', '', res)
    return res


def suggest_username(first_name, last_name=''):
    username = sanitize_name_for_login(unicode(first_name))
    if last_name:
        username += '.' + sanitize_name_for_login(unicode(last_name))
    username = username[:30]
    i = get_user_model().objects.count()
    if not username:
        username = 'agda%d' % i
    while get_user_model().objects.filter(username=username).count():
        i += 1
        username = 'agda%d' % i
    return username


class AgdaUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the
        . given email,
        favorite topping, and password.
        """
        if not email:
            msg = "Users must have an email address"
            raise ValueError(msg)

        user = self.model(
            email=AgdaUserManager.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with
        the given email,
        .
        favorite topping and password.
        """
        user = self.create_user(email, password=password)
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

email_max_length = 255


class AgdaUser(AbstractBaseUser, PermissionsMixin, AgdaModelMixin):
    """Agda specific extensions of user-model. Django 1.6 version.
    Extends the regular Django user model with Agda specific fields.
    """
    email = models.EmailField(
        verbose_name="email address",
        max_length=email_max_length,
        unique=True,
        db_index=True,
    )

    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    first_name = models.CharField('first name', max_length=30, blank=True)
    last_name = models.CharField('last name', max_length=30, blank=True)

    api_password = models.CharField(max_length=128, blank=True, null=True)

    USERNAME_FIELD = "email"

    objects = AgdaUserManager()

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    class Meta:
        verbose_name_plural = "profiles"

    api_password_characters = string.ascii_letters + string.digits + string.punctuation
    api_password_length = 20

    def __unicode__(self):
        return u"%s" % (self.get_full_name())

    def save(self, **kwargs):
        super(AgdaUser, self).save()

    def name(self):
        return (self.first_name + " " + self.last_name).strip()

    def set_api_password(self, raw_password):
        """Empty means UNUSABLE_PASSWORD."""
        # Cloned from django.contrib.auth.models.User
        self.api_password = make_password(raw_password)

    def check_api_password(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        hashing formats behind the scenes.
        """
        # Cloned from django.contrib.auth.models.User
        def setter(raw_password):
            self.set_password(raw_password)
            self.save()
        return check_password(raw_password, self.password, setter)

    def set_unusable_api_password(self):
        # Cloned from django.contrib.auth.models.User
        # Sets a value that will never be a valid hash
        self.api_password = make_password(None)

    def has_usable_api_password(self):
        # Cloned from django.contrib.auth.models.User
        return is_password_usable(self.api_password)

    def send_email(self,
                   subject,
                   template,
                   extra_dict={},
                   extra_recipients=[],
                   cc_recipients=[],
                   no_email_to_user=False,
                   sender=AGDA_MAIL_FROM):
        d = dict(profile=self,
                 agda_url=AGDA_URL_BASE + reverse('agda.views.top'))
        d.update(extra_dict)
        contents = render_to_string(template, d)
        if no_email_to_user:
            recipients = extra_recipients
        else:
            recipients = [self.email] + extra_recipients
        msg = EmailMessage(subject=subject,
                           body=contents,
                           from_email=sender,
                           to=recipients,
                           cc=cc_recipients,
                           )
        msg.send()
