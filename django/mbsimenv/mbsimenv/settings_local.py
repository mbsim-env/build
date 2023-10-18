import os.path
from .settings_base import *

MBSIMENV_TYPE='local'

DEBUG = True
DEBUG_PROPAGATE_EXCEPTIONS = not DEBUG
MEDIA_ROOT = os.path.join(BASE_DIR, "media_root")
CSRF_COOKIE_SECURE = False
LOGGING['disable_existing_loggers'] = True

DATABASES = databases(MBSIMENV_TYPE)
debug(DEBUG)
