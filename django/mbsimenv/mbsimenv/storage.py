import django
import os
import paramiko

class SimpleSFTPStorage(django.core.files.storage.Storage):

  def __init__(self):
    self.client=None
    self.sftp=None
    self.params=django.conf.settings.SIMPLE_SFTP_STORAGE_PARAMS

  def _connectOnDemandHandler(func):
    def wrapper(self, *args, **kwargs):
      def reconnect(self):
        # cleanup load connection (not error on failure)
        try:
          if self.sftp is not None:
            self.sftp.close()
        except:
          pass
        try:
          if self.client is not None:
            self.client.close()
        except:
          pass
        self.sftp=None
        self.client=None
        # new connection
        self.client=paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.client.MissingHostKeyPolicy)
        self.client.connect(self.params["hostname"], port=self.params["port"],
                            username=self.params["username"], password=self.params["password"],
                            allow_agent=False, look_for_keys=False, timeout=60, banner_timeout=60, auth_timeout=60)
        self.sftp=self.client.open_sftp()
      try:
        return func(self, *args, **kwargs)
      except:
        try:
          reconnect(self)
          return func(self, *args, **kwargs)
        except:
          reconnect(self)
          return func(self, *args, **kwargs)
    return wrapper

  @_connectOnDemandHandler
  def _open(self, name, mode='rb'):
    remotePath=os.path.join(self.params["root"], name)
    try:
      fileSize=self.sftp.stat(remotePath).st_size
    except FileNotFoundError:
      fileSize=None
    f=self.sftp.open(remotePath, mode)
    f.prefetch(fileSize)
    f.set_pipelined(True)
    return f

  @_connectOnDemandHandler
  def _save(self, name, content):
    remotePath=os.path.join(self.params["root"], name)
    with self._open(remotePath, "wb") as fo:
      while True:
        data=content.read(32768)
        if len(data)==0:
          break
        fo.write(data)
    return name

  @_connectOnDemandHandler
  def delete(self, name):
    remotePath=os.path.join(self.params["root"], name)
    try:
      self.sftp.remove(remotePath)
    except FileNotFoundError:
      pass

  @_connectOnDemandHandler
  def size(self, name):
    remotePath=os.path.join(self.params["root"], name)
    return self.sftp.stat(remotePath).st_size

  @_connectOnDemandHandler
  def exists(self, name):
    remotePath=os.path.join(self.params["root"], name)
    try:
      self.sftp.stat(remotePath)
      return True
    except FileNotFoundError:
      return False

  def url(self, name):
    # just to enable the django admin page
    return "dummy"
