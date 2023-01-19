import json
import datetime
import django
import django.utils.timezone
import os
import glob
import subprocess
import threading
import fcntl
import time
import re
import string
import socket
import sys
import enum
import importlib.util
import octicons.templatetags.octicons

# a dummy context object doing just nothing (e.g. usefull as a dummy lock(mutext) object.
class NullContext(object):
  def __enter__(self):
    return None
  def __exit__(self, exc_type, exc_val, exc_tb):
    return False 

class GithubCache(object):
  # Timeouts after that the github rights for the current user are reget from github.
  # A change of the user rights on github may only have an effect on this site after this timeout.
  viewTimeout=django.utils.timezone.timedelta(days=1) # timeout for template (things being shown to the user)
  changesTimeout=django.utils.timezone.timedelta(minutes=10) # timeout for changes on this site

  dontCache=False

  def __init__(self, request):
    if importlib.util.find_spec("github") is None:
      self.gh=None
      return

    import github
    self.request=request

    token=self.getAccessToken()
    if token:
      self.gh=github.Github(token)
    else:
      self.gh=None

  def getAccessToken(self):
    if importlib.util.find_spec("allauth") is None:
      return None

    import allauth
    if not self.request.user.is_authenticated:
      return None
    app=allauth.socialaccount.models.SocialApp.objects.get(provider="github")
    try:
      account=allauth.socialaccount.models.SocialAccount.objects.get(user=self.request.user)
    except allauth.socialaccount.models.SocialAccount.DoesNotExist:
      return None
    try:
      token=allauth.socialaccount.models.SocialToken.objects.get(app=app, account=account)
    except allauth.socialaccount.models.SocialToken.DoesNotExist:
      return None
    return token.token

  # the serialization does not store the credentials, hence we add it manually when the session cache is used
  def _addAccessToken(self, obj):
    setattr(obj._requester, "_Requester__authorizationHeader", "token " + self.getAccessToken())

  def getAuthUser(self):
    if not self.gh:
      return None
    if "githubCache" not in self.request.session:
      self.request.session["githubCache"]={}
    if GithubCache.dontCache or "authUser" not in self.request.session["githubCache"]:
      self.request.session["githubCache"]["authUser"]=self.gh.get_user()
      self.request.session.modified=True
    else:
      self._addAccessToken(self.request.session["githubCache"]["authUser"])
    return self.request.session["githubCache"]["authUser"]

  def getNamedUser(self):
    if not self.gh:
      return None
    if "githubCache" not in self.request.session:
      self.request.session["githubCache"]={}
    if GithubCache.dontCache or "namedUser" not in self.request.session["githubCache"]:
      self.request.session["githubCache"]["namedUser"]=self.gh.get_user(self.getAuthUser().login)
      self.request.session.modified=True
    else:
      self._addAccessToken(self.request.session["githubCache"]["namedUser"])
    return self.request.session["githubCache"]["namedUser"]

  def getMbsimenvOrg(self):
    if not self.gh:
      return None
    if "githubCache" not in self.request.session:
      self.request.session["githubCache"]={}
    if GithubCache.dontCache or "mbsimenvOrg" not in self.request.session["githubCache"]:
      self.request.session["githubCache"]["mbsimenvOrg"]=self.gh.get_organization("mbsim-env")
      self.request.session.modified=True
    else:
      self._addAccessToken(self.request.session["githubCache"]["mbsimenvOrg"])
    return self.request.session["githubCache"]["mbsimenvOrg"]

  def getUserInMbsimenvOrg(self, timeout):
    if not self.gh:
      return False
    if "githubCache" not in self.request.session:
      self.request.session["githubCache"]={}
    if GithubCache.dontCache or "userInMbsimenv" not in self.request.session["githubCache"] or \
       django.utils.timezone.now()-self.request.session["githubCache"]["userInMbsimenvDateTime"]>=timeout:
      self.request.session["githubCache"]["userInMbsimenv"]=self.getMbsimenvOrg().has_in_members(self.getNamedUser())
      self.request.session["githubCache"]["userInMbsimenvDateTime"]=django.utils.timezone.now()
      self.request.session.modified=True
    return self.request.session["githubCache"]["userInMbsimenv"]

  def getMbsimenvRepo(self, repo):
    if not self.gh:
      return None
    if "githubCache" not in self.request.session:
      self.request.session["githubCache"]={}
    if GithubCache.dontCache or "repo_"+repo not in self.request.session["githubCache"]:
      self.request.session["githubCache"]["repo_"+repo]=self.gh.get_repo("mbsim-env/"+repo)
      self.request.session.modified=True
    else:
      self._addAccessToken(self.request.session["githubCache"]["repo_"+repo])
    return self.request.session["githubCache"]["repo_"+repo]

  def getMbsimenvRepoBranches(self, repo, lock=NullContext()):
    if not self.gh:
      return None
    with lock:
      repo=self.getMbsimenvRepo(repo)
    return repo.get_branches()

  def getRateLimit(self):
    if not self.gh:
      return None
    return self.gh.get_rate_limit()

class SessionSerializer:
  def dumps(self, obj):
    class Serialize(json.JSONEncoder):
      def default(self, obj):
        import github
        if isinstance(obj, github.GithubObject.GithubObject):
          return {
            "__TYPE__": "github",
            "__DATA__": {
              "module": obj.__module__[len("github."):],
              "class": obj.__class__.__name__,
              "raw_data": obj.raw_data,
              "raw_headers": obj.raw_headers,
            },
          }
        if isinstance(obj, datetime.datetime):
          return {"__TYPE__": "datetime", "__DATA__": obj.strftime('%Y-%m-%dT%H:%M:%S%z') }
        return super().default(obj)
    return json.dumps(obj, cls=Serialize, separators=(',', ':')).encode('utf-8')

  def loads(self, data):
    ##### TAKE CARE HERE #####
    ##### Any bug (exception) in this routine is not displayed by django!!!
    ##### It just leads to a empty django session!!!
    ##### Hence, you will not see what's wrong with this code!
    def objSer(d):
      import github
      if '__TYPE__' in d:
        if d["__TYPE__"]=="github":
          module=getattr(github, d["__DATA__"]["module"])
          klass=getattr(module, d["__DATA__"]["class"])
          return github.Github().create_from_raw_data(klass, d["__DATA__"]["raw_data"], d["__DATA__"]["raw_headers"])
        if d["__TYPE__"]=="datetime":
          return datetime.datetime.strptime(d["__DATA__"], '%Y-%m-%dT%H:%M:%S%z')
        raise json.JSONDecodeError("Unknown __TYPE__ in JSON deserialization", "", 0)
      return d
    return json.loads(data.decode('utf-8'), object_hook=objSer)

# A file object which prints to a internal string buffer an optionally to a secon file
class MultiFile(object):
  def __init__(self, fileObj=None):
    self.data=""
    self.fileObj=fileObj
  def write(self, str):
    self.data+=str
    if self.fileObj:
      self.fileObj.write(str)
  def flush(self):
    if self.fileObj:
      self.fileObj.flush()
  def close(self):
    if self.fileObj and self.fileObj!=sys.stdout and self.fileObj!=sys.stderr:
      f.close()
  def getData(self):
    return self.data

# kill the called subprocess
def killSubprocessCall(proc, f, killed, timeout):
  killed.set()
  f.write("\n\n\n******************** START: MESSAGE FROM runexamples.py ********************\n")
  f.write("The maximal execution time (%d min) has reached (option --maxExecutionTime),\n"%(timeout))
  f.write("but the program is still running. Terminating the program now.\n")
  f.write("******************** END: MESSAGE FROM runexamples.py **********************\n\n\n\n")
  proc.terminate()
  time.sleep(30)
  # if proc has not terminated after 30 seconds kill it
  if proc.poll() is None:
    f.write("\n\n\n******************** START: MESSAGE FROM runexamples.py ********************\n")
    f.write("Program has not terminated after 30 seconds, killing the program now.\n")
    f.write("******************** END: MESSAGE FROM runexamples.py **********************\n\n\n\n")
    proc.kill()

def subprocessCheckOutput(comm, f):
  p=subprocess.run(comm, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  f.write(p.stderr.decode('utf-8'))
  return p.stdout

# decode the bytes b to utf-8 replacing invalid bytes with {{0x??}}
# returns a tuple containing the utf-8 decoded string and none processed bytes
# (none processed bytes can happen if the input b ends in the middle of a utf-8 multi-byte char)
def decodeUTF8(b):
  try:
    u=b.decode("utf-8")
    return u, b""
  except UnicodeDecodeError as ex:
    if ex.reason=="unexpected end of data":
      return b[:ex.start].decode("utf-8"), b[ex.start:]
    ustart=b[:ex.start].decode("utf-8")
    uerr=""
    for c in b[ex.start:ex.end]:
      uerr+="{{"+hex(c)+"}}"
    urest, brest=decodeUTF8(b[ex.end:])
    return ustart+uerr+urest, brest

# subprocess call with MultiFile output
def subprocessCall(args, f, env=os.environ, maxExecutionTime=0, stopRE=None):
  # remove core dumps from previous runs
  for coreFile in glob.glob("core.*")+glob.glob("vgcore.*"):
    os.remove(coreFile)
  startTime=django.utils.timezone.now()
  print("\nCalling command\n%s\nwith cwd\n%s\nat %s\n"%(" ".join(map(lambda x: "'"+x+"'", args)), os.getcwd(), startTime), file=f)
  # start the program to execute
  try:
    proc=subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, bufsize=-1, env=env)
  except OSError as ex:
    f.write("\n\n\n******************** FAILED TO START PROCESS ********************\n")
    f.write(str(ex)+"\n")
    return 1
  # a guard for the maximal execution time for the starte program
  guard=None
  killed=threading.Event()
  if maxExecutionTime>0:
    guard=threading.Timer(maxExecutionTime*60, killSubprocessCall, args=(proc, f, killed, maxExecutionTime))
    guard.start()
  # make stdout none blocking
  fd=proc.stdout.fileno()
  fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)
  # read all output
  dataNP=b'' # not already processed bytes (required since we read 100 bytes which may break a unicode multi byte character)
  sleepTime=0.01
  stopByRE=False
  while proc.poll() is None:
    time.sleep(sleepTime)
    if sleepTime<0.5: sleepTime=sleepTime*1.01
    try:
      data=dataNP+proc.stdout.read()
    except:
      continue
    dataNP=b''
    if b"\n" not in data: # process only full lines
      dataNP=data
      continue
    # remove carrige returns
    data=re.sub(b"\n.*\r", b"\n", data)
    data=re.sub(b"^.*\r", b"", data)
    # decode all data possible
    dataLine, dataNP=decodeUTF8(data)
    print(dataLine, end="", file=f)
    # check stop regex
    if stopRE is not None and stopRE.search(dataLine) is not None:
      stopByRE=True
      break
  if stopByRE:
    f.write("\n\n\n******************** START: MESSAGE FROM runexamples.py ********************\n")
    f.write("Terminating due to stop regex in output\n")
    f.write("******************** END: MESSAGE FROM runexamples.py **********************\n\n\n\n")
    proc.terminate()
    time.sleep(1)
    if proc.poll() is None:
      proc.kill()
  # print not yet processed data
  dataLine, dataNP=decodeUTF8(dataNP+b" ")
  print(dataLine, end="", file=f)
  # wait for the call program to exit
  ret=proc.wait()
  endTime=django.utils.timezone.now()
  print("\nEnded at %s after %s with exit-code %d\n"%(endTime, endTime-startTime, ret), file=f)
  # stop the execution time guard thread
  if maxExecutionTime>0:
    if killed.isSet():
      return subprocessCall.timedOutErrorCode # return to indicate that the program was terminated/killed due to a timeout
    else:
      guard.cancel()
  if stopByRE:
    return subprocessCall.stopByREErrorCode # return to indicate that the program was terminated/killed due to a stop regex
  # check for core dump file
  exeRE=re.compile("^.*LSB core file.*, *from '([^']*)' *,.*$")
  for coreFile in glob.glob("core.*")+glob.glob("vgcore.*"):
    m=exeRE.match(subprocess.check_output(["file", coreFile]).decode('utf-8'))
    if m is None:
      f.write("\n\n\nCORE DUMP file found but cannot extract executalbe name!\n\n\n")
      continue
    exe=m.group(1).split(" ")[0]
    out=subprocess.check_output(["gdb", "-q", "-n", "-ex", "bt", "-batch", exe, coreFile]).decode('utf-8')
    f.write("\n\n\n******************** START: CORE DUMP BACKTRACE OF "+exe+" ********************\n\n\n")
    f.write(out)
    f.write("\n\n\n******************** END: CORE DUMP BACKTRACE ********************\n\n\n")
  # remove core dumps (these require a lot of disc space)
  for coreFile in glob.glob("core.*")+glob.glob("vgcore.*"):
    os.remove(coreFile)
  # return the return value ot the called programm
  return ret
subprocessCall.timedOutErrorCode=1000000
subprocessCall.stopByREErrorCode=1000001
def subprocessOtherFailure(ret):
  return ret==subprocessCall.timedOutErrorCode or \
         ret==subprocessCall.stopByREErrorCode

# init django
def startLocalServer(port, onlyGetServerInfo=False):
  import builds
  pidfile=os.path.dirname(os.path.realpath(__file__))+"/../localserver.json"
  if onlyGetServerInfo and os.path.exists(pidfile):
    with open(pidfile, "r") as f:
      localserver=json.load(f)
    return {"process": None, "hostname": localserver["hostname"], "port": localserver["port"]}
  # make migrations
  try:
    builds.models.Run.objects.count()
  except django.db.utils.OperationalError:
    print("No table found in database. Run Django migration. (only done the first time)")
    django.core.management.call_command("migrate", interactive=False, traceback=True, no_color=True)
  # start server
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    result=sock.connect_ex(('localhost',port))
    if result!=0:
      print("No server is running. Starting server. (only done the first time)")
      env=os.environ.copy()
      env['DJANGO_SETTINGS_MODULE']='mbsimenv.settings_'+django.conf.settings.MBSIMENV_TYPE
      p=subprocess.Popen([sys.executable, os.path.dirname(os.path.realpath(__file__))+"/../manage.py",
                          "runserver", "--insecure", "--noreload", "localhost:"+str(port)],
                         preexec_fn=os.setpgrp, env=env)
      with open(pidfile, "w") as f:
        json.dump({"hostname": "localhost", "port": port}, f)
    else:
      p=None
      print("A server is already running. Skipping starting another one.")

  with open(pidfile, "r") as f:
    localserver=json.load(f)
  return {"process": p, "hostname": localserver["hostname"], "port": localserver["port"]}

def tooltip(text, tooltip):
  return '<span data-toggle="tooltip" data-placement="bottom" title="%s">%s</span>'%(tooltip, text)

def copyFile(fi, fo):
  if type(fi)==bytes:
    fo.write(fi)
  else:
    while True:
      data=fi.read(32768)
      if len(data)==0:
        break
      fo.write(data)

getExecutorIDRE=re.compile("\WMBSIMENV_EXECUTOR_([a-zA-Z0-9_]+)")
def getExecutorID(executor):
  m=getExecutorIDRE.search(executor)
  if m is not None:
    return m.group(1)
  return None

def buildTypeIcon(buildType):
  ret=""
  if "linux64" in buildType:
    ret+='<i class="fa-brands fa-linux"></i>'
  if "win64" in buildType:
    ret+='<i class="fa-brands fa-windows"></i>'
  if "release" in buildType:
    ret+='<i class="fa-solid fa-building"></i>'
  if "debug" in buildType or "-ci" in buildType:
    ret+=octicons.templatetags.octicons.octicon("bug")
  if "docker" in buildType:
    ret+='<i class="fa-brands fa-docker"></i>'
  return ret

# add labels to fields
class FieldLabel(enum.Enum):
  inline = 1
  list = 2
  search = 3
def addFieldLabel(field, *args):
  setattr(field, "mbsimenv_labels", args)
  return field

def bulk_create(model, objs, refresh=True):
  # workaround for  django>=3.2 issue https://code.djangoproject.com/ticket/33649
  # (this issue is considered a feature since django>=3.2)
  # remove objects where the PK is already set
  # (ignore_conflicts on bulk_create is no longer working)
  objs=list(filter(lambda o: o.pk is None, objs))
  if len(objs)==0:
    return
  # needed since django.db.models.signals.pre_save.connect(...) is not called by bulk_create
  django.db.close_old_connections()
  # bulk create objects
  model.objects.bulk_create(objs)
  # if a refresh (update of the PK of the python objects) is requested and the PK is not set ...
  # (note: this will never happen e.g. for postgres since it supports the update already on
  #  bulk_create; but e.g. sqlite does not update and needs this code)
  if refresh and objs[0].pk is None:
    # ... reload the created objects from the DB and set the PK of the corresponding python objects
    for idUUID in model.objects.filter(uuid__in=[o.uuid for o in objs]).values_list("pk", "uuid"):
      next(filter(lambda o: o.uuid==idUUID[1], objs)).pk=idUUID[0]

def urls_path(*argv, robots=True, **kwargs):
  path=django.urls.path(*argv, **kwargs)
  path.robots=robots
  return path
