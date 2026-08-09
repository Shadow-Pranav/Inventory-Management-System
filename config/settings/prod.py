from decouple import config

from .base import *  # noqa: F403
from .base import env_to_bool

DEBUG = False
STRICT_TENANCY = True

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=env_to_bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 7, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
