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
import mbsimenv
import builds
import socket
import sys

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
    import github
    self.request=request

    token=self.getAccessToken()
    if token:
      self.gh=github.Github(token)
    else:
      self.gh=None

  def getAccessToken(self):
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

# subprocess call with MultiFile output
def subprocessCall(args, f, env=os.environ, maxExecutionTime=0):
  # remove core dumps from previous runs
  for coreFile in glob.glob("*core*"):
    if "LSB core file" in subprocess.check_output(["file", coreFile]).decode('utf-8'):
      os.remove(coreFile)
  # start the program to execute
  proc=subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, bufsize=-1, env=env)
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
  lineNP=b'' # not already processed bytes (required since we read 100 bytes which may break a unicode multi byte character)
  while proc.poll() is None:
    time.sleep(0.5)
    try:
      line=lineNP+proc.stdout.read()
    except:
      continue
    lineNP=b''
    try:
      print(line.decode("utf-8"), end="", file=f)
    except UnicodeDecodeError as ex: # catch broken multibyte unicode characters and append it to next line
      print(line[0:ex.start].decode("utf-8"), end="", file=f) # print up to first broken character
      lineNP=ex.object[ex.start:] # add broken characters to next line
  # wait for the call program to exit
  ret=proc.wait()
  # stop the execution time guard thread
  if maxExecutionTime>0:
    if killed.isSet():
      return subprocessCall.timedOutErrorCode # return to indicate that the program was terminated/killed
    else:
      guard.cancel()
  # check for core dump file
  exeRE=re.compile("^.*LSB core file.*, *from '([^']*)' *,.*$")
  for coreFile in glob.glob("*core*"):
    m=exeRE.match(subprocess.check_output(["file", coreFile]).decode('utf-8'))
    if m is None: continue
    exe=m.group(1).split(" ")[0]
    out=subprocess.check_output(["gdb", "-q", "-n", "-ex", "bt", "-batch", exe, coreFile]).decode('utf-8')
    f.write("\n\n\n******************** START: CORE DUMP BACKTRACE OF "+exe+" ********************\n\n\n")
    f.write(out)
    f.write("\n\n\n******************** END: CORE DUMP BACKTRACE ********************\n\n\n")
  # return the return value ot the called programm
  return ret
subprocessCall.timedOutErrorCode=1000000

# init django
def startLocalServer(port):
  # make migrations
  try:
    builds.models.Run.objects.count()
  except django.db.utils.OperationalError:
    print("No table found in database. Run Django migration. (only done the first time)")
    django.core.management.call_command("migrate", interactive=False, traceback=True, no_color=True)
  # start server
  sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  result=sock.connect_ex(('localhost',port))
  if result!=0:
    print("No server is running. Starting server. (only done the first time)")
    fnull=open(os.devnull, 'w')
    subprocess.Popen([sys.executable, os.path.dirname(os.path.realpath(__file__))+"/../manage.py", "runserver", "--insecure", "localhost:"+str(port)],
                     stderr=fnull, stdout=fnull)
    with open(os.path.dirname(os.path.realpath(__file__))+"/../localserver.json", "w") as f:
      json.dump({"hostname": "localhost", "port": port}, f)
  sock.close()
