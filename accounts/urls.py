from django.urls import path
from .forms import CampusAuthenticationForm
from .views import (
    CampusLoginView,
    ProfileDetailView,
    ProfileUpdateView,
    SignUpView,
    logout_view,
)

urlpatterns = [
    path(
        "login/",
        CampusLoginView.as_view(authentication_form=CampusAuthenticationForm),
        name="login",
    ),
    path("logout/", logout_view, name="logout"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("profile/", ProfileDetailView.as_view(), name="profile"),
    path("profile/edit/", ProfileUpdateView.as_view(), name="profile_edit"),
]