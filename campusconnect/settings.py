"""
Django settings for campusconnect project (FixIT Repair).
"""

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Load KEY=value lines from a .env file next to manage.py (if present).
# Real environment variables always win over the file. .env is in .gitignore.
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8-sig").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _value = _line.split("=", 1)
        os.environ.setdefault(_key.strip(), _value.strip().strip("\"'"))


# True while running "python manage.py test" so the test run never touches the
# real database and never needs production-only security settings.
TESTING = "test" in sys.argv

# DEBUG is OFF unless .env (or the environment) explicitly turns it on.
DEBUG = os.environ.get("DJANGO_DEBUG", "false").strip().lower() == "true"

# The secret key comes from .env. Only DEBUG/test runs may use a throwaway key.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or TESTING:
        SECRET_KEY = "django-insecure-local-development-only"
    else:
        raise ImproperlyConfigured(
            "Set DJANGO_SECRET_KEY in your .env file "
            "(copy .env.example to .env and fill it in)."
        )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]
if DEBUG:
    ALLOWED_HOSTS.append("testserver")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    "accounts",
    "dashboard",
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'campusconnect.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'campusconnect.wsgi.application'


# Database
#
# Which database is used (first match wins):
#   1. DATABASE_URL set        -> PostgreSQL (Supabase). Use the *Session pooler*
#                                 URI if your network has no IPv6 support.
#   2. POSTGRES_HOST set       -> local/other PostgreSQL via POSTGRES_* variables
#   3. nothing set (default)   -> local SQLite file (db.sqlite3)
# Set USE_SQLITE=true to force SQLite even if the variables above are set.
# Running "python manage.py test" always uses SQLite (see TESTING above).

# Seconds to wait for PostgreSQL before giving up (prevents silent hangs).
DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "10"))

use_sqlite = TESTING or os.environ.get("USE_SQLITE", "false").lower() == "true"
database_url = os.environ.get("DATABASE_URL")


def _parse_database_url(url):
    """Parse a PostgreSQL URI without urlparse() choking on '[', ']' or '!' in
    the password (Python treats '[...]' in the userinfo part as an IPv6 host)."""
    scheme, sep, rest = url.strip().partition("://")
    if not sep or scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured(
            "DATABASE_URL must start with postgresql:// (copy it from "
            "Supabase > Connect > Session pooler)."
        )
    rest, _, query = rest.partition("?")
    authority, slash, db_name = rest.partition("/")
    userinfo, at, hostport = authority.rpartition("@")
    if not at or not hostport:
        raise ImproperlyConfigured("DATABASE_URL is missing user:password@host.")
    user, _, password = userinfo.partition(":")
    host, _, port = hostport.partition(":")
    if not host or not db_name:
        raise ImproperlyConfigured("DATABASE_URL needs a host and database name.")
    try:
        port = int(port) if port else 5432
    except ValueError as exc:
        raise ImproperlyConfigured(
            "DATABASE_URL contains an invalid PostgreSQL port."
        ) from exc
    user, password = unquote(user), unquote(password)
    if password.startswith("[") and password.endswith("]"):
        import warnings

        warnings.warn(
            "Your database password is wrapped in [ ]. Supabase shows "
            "[YOUR-PASSWORD] as a placeholder: remove the brackets unless "
            "they are really part of the password.",
            stacklevel=2,
        )
    return {
        "NAME": unquote(db_name),
        "USER": user,
        "PASSWORD": password,
        "HOST": host,
        "PORT": port,
        "OPTIONS": parse_qs(query),
    }


if not use_sqlite and database_url:
    _db = _parse_database_url(database_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _db["NAME"],
            "USER": _db["USER"],
            "PASSWORD": _db["PASSWORD"],
            "HOST": _db["HOST"],
            "PORT": _db["PORT"],
            "CONN_MAX_AGE": 0,
            # Supabase transaction pooler (port 6543) cannot use server-side cursors.
            "DISABLE_SERVER_SIDE_CURSORS": _db["PORT"] == 6543,
            "OPTIONS": {
                "sslmode": _db["OPTIONS"].get("sslmode", ["require"])[0],
                "connect_timeout": DB_CONNECT_TIMEOUT,
            },
        }
    }
elif not use_sqlite and os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "fixit"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "OPTIONS": {
                "connect_timeout": DB_CONNECT_TIMEOUT,
            },
        }
    }
else:
    if not use_sqlite and not TESTING:
        import warnings

        warnings.warn(
            "DATABASE_URL is not set -> using local SQLite (db.sqlite3). "
            "New accounts will NOT be saved to Supabase.",
            stacklevel=1,
        )
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files

STATIC_URL = 'static/'


# Email

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "false").lower() == "true"

AUTH_USER_MODEL = 'accounts.CustomUser'
AUTHENTICATION_BACKENDS = ["accounts.backends.EmailBackend"]
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'


# Security

# Origins allowed to POST to the site over HTTPS (comma separated, from .env).
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Browser-side protections (safe in every environment).
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# HTTPS-only protections for real deployments (DEBUG off, not running tests).
if not DEBUG and not TESTING:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True