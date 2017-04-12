import datetime
import binascii
import os

from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import _user_has_perm, _user_get_all_permissions, _user_has_module_perms

import mongoengine
from mongoengine.django import auth
from mongoengine import fields, Document, ImproperlyConfigured


class User(Document):
    """
    VERSION ISSUES:

    In Mongoengine <= 0.9 there is a mongoengine.django subpackage, which
    implements mongoengine User document and its integration with django
    authentication system.

    In Mongoengine >= 0.10 mongoengine.django was extracted from Mongoengine
    codebase and moved into a separate repository - django-mongoengine. That
    repository contains an AbstractBaseUser class, so that you can just
    inherit your User model from it, instead of copy-pasting the following
    200 lines of boilerplate code from mongoengine.django.auth.User.
    """
    id = fields.IntField(primary_key=True)
    username = fields.StringField(required=True)
    email = fields.EmailField()

    # name is a human-readable name used to refer to user e.g. "Martin Taylor"
    # longest full name registered in guinness book is 744 letters-long
    name = fields.StringField()
    password = fields.StringField(
        max_length=128,
        verbose_name=_('password'),
        help_text=_("Use '[algo]$[iterations]$[salt]$[hexdigest]' or use the <a href=\"password/\">change password form</a>.")
    )

    # the following DjangoORM-like fields are defined
    # just like in mongoengine.django.auth.User
    is_staff = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)

    last_login = fields.DateTimeField(default=timezone.now, verbose_name=_('last login'))
    date_joined = fields.DateTimeField(default=timezone.now, verbose_name=_('date joined'))
    user_permissions = fields.ListField(
        fields.ReferenceField(auth.Permission),
        verbose_name=_('user permissions'),
        help_text=_('Permissions for the user.')
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

    def get_short_name(self):
        return self.username

    def get_full_name(self):
        return self.username

    def __unicode__(self):
        return self.username

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def set_password(self, raw_password):
        """
        Sets the user's password - always use this rather than directly
        assigning to :attr:`~mongoengine.django.auth.User.password` as the
        password is hashed before storage.
        """
        self.password = make_password(raw_password)
        self.save()
        return self

    def check_password(self, raw_password):
        """
        Checks the user's password against a provided password - always use
        this rather than directly comparing to
        :attr:`~mongoengine.django.auth.User.password` as the password is
        hashed before storage.
        """
        return check_password(raw_password, self.password)

    @classmethod
    def create_user(cls, username, password, email=None):
        """
        Create (and save) a new user with the given username, password and
        email address.
        """
        now = datetime.datetime.now()

        # Normalize the address by lowercasing the domain part of the email
        # address.
        if email is not None:
            try:
                email_name, domain_part = email.strip().split('@', 1)
            except ValueError:
                pass
            else:
                email = '@'.join([email_name, domain_part.lower()])

        user = cls(username=username, email=email, date_joined=now)
        user.set_password(password)
        user.save()
        return user

    def get_group_permissions(self, obj=None):
        """
        Returns a list of permission strings that this user has through his/her
        groups. This method queries all available auth backends. If an object
        is passed in, only permissions matching this object are returned.
        """
        permissions = set()
        for backend in auth.get_backends():
            if hasattr(backend, "get_group_permissions"):
                permissions.update(backend.get_group_permissions(self, obj))
        return permissions

    def get_all_permissions(self, obj=None):
        return _user_get_all_permissions(self, obj)

    def has_perm(self, perm, obj=None):
        """
        Returns True if the user has the specified permission. This method
        queries all available auth backends, but returns immediately if any
        backend returns True. Thus, a user who has permission from a single
        auth backend is assumed to have permission in general. If an object is
        provided, permissions for this specific object are checked.
        """

        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_module_perms(self, app_label):
        """
        Returns True if the user has any permissions in the given app label.
        Uses pretty much the same logic as has_perm, above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)

    def email_user(self, subject, message, from_email=None):
        "Sends an e-mail to this User."
        from django.core.mail import send_mail
        send_mail(subject, message, from_email, [self.email])

    def get_profile(self):
        """
        Returns site-specific profile for this user. Raises
        SiteProfileNotAvailable if this site does not allow profiles.
        """
        if not hasattr(self, '_profile_cache'):
            from django.conf import settings
            if not getattr(settings, 'AUTH_PROFILE_MODULE', False):
                raise auth.SiteProfileNotAvailable('You need to set AUTH_PROFILE_MO'
                                              'DULE in your project settings')
            try:
                app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
            except ValueError:
                raise auth.SiteProfileNotAvailable('app_label and model_name should'
                        ' be separated by a dot in the AUTH_PROFILE_MODULE set'
                        'ting')

            try:
                model = models.get_model(app_label, model_name)
                if model is None:
                    raise auth.SiteProfileNotAvailable('Unable to load the profile '
                        'model, check AUTH_PROFILE_MODULE in your project sett'
                        'ings')
                self._profile_cache = model._default_manager.using(self._state.db).get(user__id__exact=self.id)
                self._profile_cache.user = self
            except (ImportError, ImproperlyConfigured):
                raise auth.SiteProfileNotAvailable
        return self._profile_cache


@python_2_unicode_compatible
class Token(Document):
    """
    This is a mongoengine adaptation of DRF's default Token.

    The default authorization token model.
    """
    key = fields.StringField(required=True)
    user = fields.ReferenceField(User, reverse_delete_rule=mongoengine.CASCADE)
    created = fields.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __str__(self):
        return self.key
