import os.path
from .settings_base import *

MBSIMENV_TYPE='buildsystem'

DEBUG = False
SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
LOGGING['disable_existing_loggers'] = False

DATABASES = databases(MBSIMENV_TYPE)
debug(DEBUG)


# file storage
def filestorageServerAndPort():
  if "MBSIMENVFILESTORAGE" not in os.environ:
    return ["filestorage", 1122]
  x=os.environ["MBSIMENVFILESTORAGE"].split(":")
  return [x[0], int(x[1])]
DEFAULT_FILE_STORAGE="mbsimenv.storage.SimpleSFTPStorage"
SIMPLE_SFTP_STORAGE_PARAMS={
  "hostname": filestorageServerAndPort()[0],
  "port": filestorageServerAndPort()[1],
  "root": "/data/databasemedia/",
  "username": "dockeruser",
  "password": mbsimenvSecrets.getSecrets("filestoragePassword"),
}
