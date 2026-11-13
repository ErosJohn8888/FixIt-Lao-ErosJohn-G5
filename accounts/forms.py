from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm as DjangoAdminUserCreationForm,
    AuthenticationForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError
from .models import CustomUser


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = (
                "form-check-input"
                if isinstance(field.widget, forms.CheckboxInput)
                else "form-control"
            )
            field.widget.attrs["class"] = css_class

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        users_with_email = CustomUser.objects.filter(email__iexact=email)
        if self.instance.pk:
            users_with_email = users_with_email.exclude(pk=self.instance.pk)
        if users_with_email.exists():
            raise ValidationError("An account with this email already exists.")
        return email


class CustomUserCreationForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email", "first_name", "last_name", "phone")


class AdminUserCreationForm(DjangoAdminUserCreationForm):
    class Meta(DjangoAdminUserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email", "first_name", "last_name", "role", "phone")


class CampusAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Invalid email or password.",
    }
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )


class ProfileUpdateForm(BootstrapFormMixin, forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "phone")