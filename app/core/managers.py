from django.contrib.auth.models import BaseUserManager
from django.db import transaction


class UserManager(BaseUserManager):

    def _create_user(self, email, password, **extra_fields):
        try:
            if not email:
                raise ValueError('The email must be set')
            if not extra_fields.get("username"):
                raise ValueError('The username must be set')
            if not password:
                raise ValueError('The password must be set')
            with transaction.atomic():
                user = self.model(email=email, **extra_fields)
                user.set_password(password)
                user.save(using=self._db)
                return user
        except Exception:
            raise

    def create_user(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        if not extra_fields.get('username'):
            extra_fields['username'] = email.split("@")[0]
        return self._create_user(email, password=password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields.get('username'):
            extra_fields['username'] = email.split("@")[0]
        return self._create_user(email, password=password, **extra_fields)
