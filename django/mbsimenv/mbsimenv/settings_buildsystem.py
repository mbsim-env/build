import os.path
from .settings_base import *

MBSIMENV_TYPE='buildsystem'

MEDIA_ROOT = "/databasemedia"
SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
LOGGING['disable_existing_loggers'] = False

DATABASES = databases(MBSIMENV_TYPE)
