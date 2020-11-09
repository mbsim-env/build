import os.path
from .settings_base import *

MBSIMENV_TYPE='localdocker'

MEDIA_ROOT = os.path.join(BASE_DIR, "media_root")
SECURE_SSL_REDIRECT = False
CSRF_COOKIE_SECURE = False
LOGGING['disable_existing_loggers'] = False

DATABASES = databases(MBSIMENV_TYPE)
