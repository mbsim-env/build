import os.path
import os
from .settings_base import *

MBSIMENV_TYPE='localdocker'

DEBUG = "MBSIMENVDEBUG" in os.environ
MEDIA_ROOT = os.path.join(BASE_DIR, "media_root")
CSRF_COOKIE_SECURE = False
LOGGING['disable_existing_loggers'] = False

DATABASES = databases(MBSIMENV_TYPE)
debug(DEBUG)
