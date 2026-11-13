from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        STAFF = "STAFF", "Staff"
        MANAGER = "MANAGER", "Manager"

    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.STAFF
    )
    email = models.EmailField(blank=False)
    phone = models.CharField(max_length=30, blank=True)

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=["STAFF", "MANAGER"]),
                name="accounts_customuser_valid_role",
            ),
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_customuser_email_ci_unique",
            ),
        ]

    def __str__(self):
        return self.username