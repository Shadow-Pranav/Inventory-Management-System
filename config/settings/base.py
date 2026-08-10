from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_to_bool(value: str) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "on")


SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=env_to_bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

STRICT_TENANCY = config("STRICT_TENANCY", default=True, cast=env_to_bool)

# apps/core/audit.py connects pre_save/post_save/post_delete receivers for each of these.
# Every entry must either be "tenancy.Organization" itself or a model with an `organization`
# FK — apps/core/audit.py::_record() drops the row silently if it can't attribute one.
AUDITED_MODELS = [
    "tenancy.Organization",
    "tenancy.Department",
    "tenancy.Membership",
    "catalog.Item",
    "catalog.Category",
    "catalog.Supplier",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "django_celery_beat",
    "django_extensions",
    "axes",
    "apps.core",
    "apps.tenancy",
    "apps.catalog",
    "apps.inventory",
    "apps.issuance",
]

AUTH_USER_MODEL = "tenancy.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.tenancy.middleware.OrganizationMiddleware",
    "apps.tenancy.middleware.ForcePasswordChangeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "axes.middleware.AxesMiddleware",  # must be last — axes docs
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",  # must be first — locks out before ModelBackend checks
    "django.contrib.auth.backends.ModelBackend",
]

# Login rate limiting (context 04 §8). Explicit AXES_LOCKOUT_PARAMETERS, not the library
# default (bare "ip_address" as of axes 6.5) — SRMS institutions have shared-lab networks
# where dozens of students sit behind one IP; locking on IP alone means one mistyped
# password locks out the whole lab. The nested list is deliberate, not decorative: axes
# treats a flat list (["username", "ip_address"]) as two INDEPENDENT lockout dimensions —
# OR semantics, so an IP still gets globally locked after N failures from any accounts on
# it. A single nested group ([["username", "ip_address"]]) tracks the *pair* as one bucket
# instead — a lockout only follows repeated failures against one specific account from one
# specific source; verified via the container's own "AXES: BEGIN ... blocking by" log line.
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hour
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False

# Session expiry: idle timeout, not a fixed calendar expiry — SESSION_SAVE_EVERY_REQUEST
# resets the clock on activity, so an active store clerk mid-shift isn't logged out, but a
# forgotten terminal is, within the hour.
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 hours of inactivity
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.trust_name",
                "apps.tenancy.context_processors.available_organizations",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="sits"),
        "USER": config("DB_USER", default="sits"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = config("TIME_ZONE", default="Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

REDIS_URL = config("REDIS_URL", default="redis://redis:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/1")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/2")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

EMAIL_HOST = config("EMAIL_HOST", default="mailhog")
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="sits@srms.local")

TRUST_NAME = config("TRUST_NAME", default="Shri Ram Murti Smarak Trust")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
