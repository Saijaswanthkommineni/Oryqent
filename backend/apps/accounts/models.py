import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_platform_admin = models.BooleanField(
        default=False,
        help_text="Grants platform-wide administration. This is not an institution role.",
    )
    auth_version = models.PositiveBigIntegerField(
        default=0,
        help_text="Invalidates previously issued access and refresh tokens when incremented.",
    )
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["is_platform_admin"], name="accounts_user_platform_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().casefold()
        super().save(*args, **kwargs)

    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.full_name.split(" ", 1)[0] if self.full_name else self.email

    def __str__(self) -> str:
        return self.email
