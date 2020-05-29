# imports
import json
import urllib.parse
import requests
import hmac
import hashlib
import time
import threading
import fcntl
import datetime
import http.cookies
import re
import shutil
import types

# wSGI entry point
def application(environ, start_response):
  startResponseCalled=False
  try:
    # get the script action = path info after the script url
    action=environ.get('PATH_INFO', None)
    method=environ.get('REQUEST_METHOD', None)

    if action=="/login" and method=="GET":
      # start_response is called inside of actionLogin
      response_data=actionLogin(environ, start_response)
    elif action=="/filtergithubfeed" and method=="GET":
      # start_response is called inside of actionLogin
      response_data=actionFiltergithubfeed(environ, start_response)
    else:
      # start_response is called now
      start_response('200 OK', [('Content-type', 'application/json'),
                                ('Access-Control-Allow-Credentials', 'true')])
      startResponseCalled=True

      if action=="/logout" and method=="GET":
        response_data=actionLogout(environ)
      elif action=="/getcheck" and method=="GET":
        response_data=actionGetcheck(environ)
      elif action=="/setcheck" and method=="POST":
        response_data=actionSetcheck(environ)
      elif action=="/getcibranches" and method=="GET":
        response_data=actionGetcibranches(environ)
      elif action=="/addcibranch" and method=="POST":
        response_data=actionAddcibranches(environ)
      elif action=="/delcibranch" and method=="POST":
        response_data=actionDelcibranches(environ)
      elif action=="/getuser" and method=="GET":
        response_data=actionGetuser(environ)
      elif action=="/webhook" and method=="POST":
        response_data=actionWebhook(environ)
      elif action=="/releasedistribution" and method=="POST":
        response_data=actionReleasedistribution(environ)
      elif action=="/checkmbsimenvsessionid" and method=="POST":
        response_data=actionCheckmbsimenvsessionid(environ)
      else:
        response_data={'success': False, 'message': "Internal error: Unknown action or request method: "+action}

    if type(response_data)==dict: # json
      return [json.dumps(response_data).encode('utf-8')]
    if type(response_data)==bytes: # as defined by start_response(...)
      return [response_data]
    return [] # everything else
  except:
    import traceback
    if not startResponseCalled:
      start_response('200 OK', [('Content-type', 'application/json'),
                                ('Access-Control-Allow-Credentials', 'true')])
    # reset all output and generate a json error message
    response_data={}
    response_data['success']=False
    response_data['message']="Internal error: Please report the following error to the maintainer:\n"+traceback.format_exc()
    return [json.dumps(response_data).encode('utf-8')]

# config file: this will lock the config file for the lifetime of this object
class ConfigFile(object):
  def __init__(self, rw):
    self.rw=rw
  def __enter__(self):
    configFilename="/mbsim-config/mbsimBuildService.conf"
    if self.rw:
      self.fd=open(configFilename, 'r+')
      fcntl.lockf(self.fd, fcntl.LOCK_EX)
      self.config=json.load(self.fd)
    else:
      fd=open(configFilename, 'r')
      fcntl.lockf(fd, fcntl.LOCK_SH)
      self.config=json.load(fd)
      fcntl.lockf(fd, fcntl.LOCK_UN)
      fd.close()
    return self.config
  def __exit__(self, exc_type, exc_value, traceback):
    if self.rw:
      self.fd.seek(0)
      json.dump(self.config, self.fd, indent=2)
      self.fd.truncate()
      fcntl.lockf(self.fd, fcntl.LOCK_UN)
      self.fd.close()

def checkCredicals(environ, config, sessionid=None):
  if sessionid is None and 'HTTP_COOKIE' in environ:
    cookie=environ["HTTP_COOKIE"]
    c=http.cookies.SimpleCookie(cookie)
    if 'mbsimenvsessionid' in c:
      sessionid=c['mbsimenvsessionid'].value
    else:
      sessionid=None
  # check
  response_data={'success': False, 'message': 'Unknown'}
  if sessionid is None:
    response_data['success']=False
    response_data['message']="Not logged in."
  else:
    # check whether sessionid is known by the server (logged in)
    if sessionid not in config['session']:
      response_data['success']=False
      response_data['message']="Unknown session ID."
    else:
      # get access token for login
      access_token=config['session'][sessionid]['access_token']
      # check whether the sessionid is correct
      if not hmac.compare_digest(hmac.new(config['client_secret'].encode('utf-8'), access_token.encode('utf-8'), hashlib.sha1).hexdigest(), sessionid):
        response_data['success']=False
        response_data['message']="Invalid access token hmac! Maybe the login was faked! If not, try to relogin again."
      else:
        # check whether this login is permitted to save data on the server (query github collaborators)
        headers={'Authorization': 'token '+access_token,
                 'Accept': 'application/vnd.github.v3+json'}
        login=config['session'][sessionid]['login']
        response=requests.get('https://api.github.com/teams/1451964/memberships/%s'%(login), headers=headers)
        if response.status_code!=200:
          response_data['success']=False
          response_data['message']="Not allowed, since you ("+login+") are not a member of the team Developers of the organization mbsim-env. Please login as a user with valid permissions."
        elif response.json()['state']!='active':
          response_data['success']=False
          response_data['message']="Not allowed, since your ("+login+") status in the team Developers of the organization mbsim-env is pending."
        else:
          response_data['success']=True
  return response_data

# remove all sessionid's with username login from config
def removeLogin(config, login):
  so=config['session']
  sn={}
  for s in so:
    if so[s]['login']!=login:
      sn[s]=so[s]
  config['session']=sn

def requestsPost(environ, out, url, headers, dataJson):
  if environ["MBSIMENVTAGNAME"]=="latest":
    return requests.post(url, headers=headers, data=json.dumps(dataJson))
  else:
    # fake post request
    out['message']=out['message']+"\n"+"Skipping post request to\n"+url+"\nwith data\n"+\
                   json.dumps(dataJson, indent=2).replace("\\n", "\n")+\
                   "\nand header\n"+json.dumps(headers, indent=2).replace("\\n", "\n")
    response=types.SimpleNamespace()
    response.status_code=201
    response.json=lambda: {'sha': '0123456789012345678901234567890123456789'}
    return response

def actionLogin(environ, start_response):
  # get the github code passed provided by html get methode
  response_data={}
  query=urllib.parse.parse_qs(environ['QUERY_STRING'])
  if 'error' in query:
    start_response('200 OK', [('Content-type', 'application/json'),
                              ('Access-Control-Allow-Credentials', 'true')])
    startResponseCalled=True
    response_data['success']=False
    response_data['message']="Authorization request failed: "+query['error']
  else:
    code=query['code']
    with ConfigFile(True) as config:
      # get access token from github (as a json response)
      data={'client_id': config['client_id'], 'client_secret': config['client_secret'], 'code': code}
      headers={'Accept': 'application/json'}
      response=requests.post('https://github.com/login/oauth/access_token', headers=headers, data=data).json()
      if 'error' in response:
        start_response('200 OK', [('Content-type', 'application/json'),
                                  ('Access-Control-Allow-Credentials', 'true')])
        startResponseCalled=True
        response_data['success']=False
        response_data['message']="Access token request failed: "+response['error']
      else:
        access_token=response['access_token']
        # get github login name using github API request
        headers={'Authorization': 'token '+access_token,
                 'Accept': 'application/vnd.github.v3+json'}
        response=requests.get('https://api.github.com/user', headers=headers)
        if response.status_code!=200:
          start_response('200 OK', [('Content-type', 'application/json'),
                                    ('Access-Control-Allow-Credentials', 'true')])
          startResponseCalled=True
          response_data['success']=False
          response_data['message']="Internal error. Cannot get user information."
        else:
          response=response.json()
          login=response['login']
          # redirect to the example web side and pass login and access token hmac as http get methode
          sessionid=hmac.new(config['client_secret'].encode('utf-8'), access_token.encode('utf-8'), hashlib.sha1).hexdigest()
          # save login and access token in a dictionary on the server (first remove all sessionid for login than add new sessionid)
          removeLogin(config, login)
          config['session'][sessionid]={'access_token': access_token,
                                        'login': login,
                                        'avatar_url': response['avatar_url'],
                                        'name': response['name']}
          # create cookie
          c=http.cookies.SimpleCookie()
          # sessionid cookie not visible to javascript
          c['mbsimenvsessionid']=sessionid
          c['mbsimenvsessionid']['comment']="Session ID for "+environ['HTTP_HOST']
          c['mbsimenvsessionid']['domain']=environ['HTTP_HOST']
          c['mbsimenvsessionid']['path']='/'
          c['mbsimenvsessionid']['secure']=True
          c['mbsimenvsessionid']['httponly']=True
          # javascript cookie just to show the the user is logged in
          c['mbsimenvsessionid_js']="logged_in"
          c['mbsimenvsessionid_js']['comment']="User logged into for "+environ['HTTP_HOST']
          c['mbsimenvsessionid_js']['domain']=environ['HTTP_HOST']
          c['mbsimenvsessionid_js']['path']='/'
          c['mbsimenvsessionid_js']['secure']=True

          headers=[('Location', "https://"+environ['HTTP_HOST']+"/mbsim/html/index.html")]
          headers.extend(("Set-Cookie", morsel.OutputString()) for morsel in c.values())
          start_response('301 Moved Permanently', headers)
          startResponseCalled=True
          response_data=None
  return response_data

def actionLogout(environ):
  # get login
  response_data={}
  if 'HTTP_COOKIE' in environ:
    c=http.cookies.SimpleCookie(environ["HTTP_COOKIE"])
    if 'mbsimenvsessionid' in c:
      sessionid=c['mbsimenvsessionid'].value
    else:
      sessionid=None
  else:
    sessionid=None
  if sessionid is None:
    response_data['success']=True
    response_data['message']="Nobody to log out."
  else:
    with ConfigFile(True) as config:
      # remove all sessionids for login from server config
      removeLogin(config, config['session'][sessionid]['login'])
      # generate json response
      response_data['success']=True
      response_data['message']="Logged out from server."
  return response_data
  
def actionGetcheck(environ):
  # return current checked examples
  response_data={}
  with ConfigFile(False) as config: pass
  # not json input via http post required
  # return the checkedExamples entries of the config as json response
  response_data['success']=True
  response_data['message']="To be updated examples loaded."
  response_data['checkedExamples']=config['checkedExamples']
  return response_data
  
def actionSetcheck(environ):
  # save checked examples (if logged in)
  with ConfigFile(True) as config:
    response_data=checkCredicals(environ, config)
    data=json.load(environ['wsgi.input'])
    if response_data['success']:
      # save checked examples
      config['checkedExamples']=data['checkedExamples']
      # response
      response_data['success']=True
      response_data['message']="Successfully saved."
  return response_data

def actionGetcibranches(environ):
  # return current ci branches of all repos
  response_data={}
  with ConfigFile(False) as config: pass
  repos=['fmatvec', 'hdf5serie', 'openmbv', 'mbsim']
  # use a authentificated request if logged in (to avoid rate limit problems on github)
  headers={'Accept': 'application/vnd.github.v3+json'}
  if 'HTTP_COOKIE' in environ:
    c=http.cookies.SimpleCookie(environ["HTTP_COOKIE"])
    if 'mbsimenvsessionid' in c:
      sessionid=c['mbsimenvsessionid'].value
    else:
      sessionid=None
    if sessionid is not None and sessionid in config['session']:
      headers['Authorization']='token '+config['session'][sessionid]['access_token']
  # worker function to make github api requests in parallel
  def getBranch(repo, out):
    response=requests.get('https://api.github.com/repos/mbsim-env/'+repo+'/branches', headers=headers)
    if response.status_code==200:
      out.extend([b['name'] for b in response.json()])
  # start worker threads
  thread={}
  out={}
  for repo in repos:
    out[repo]=[]
    thread[repo]=threading.Thread(target=getBranch, args=(repo, out[repo]))
    thread[repo].start()
  # wait for all threads
  for repo in repos:
    thread[repo].join()
  # generate output
  curcibranch=config['curcibranch']
  response_data['success']=True
  response_data['message']="Continuous integration braches loaded."
  response_data['curcibranch']=curcibranch
  response_data['fmatvecbranch']=out['fmatvec']
  response_data['hdf5seriebranch']=out['hdf5serie']
  response_data['openmbvbranch']=out['openmbv']
  response_data['mbsimbranch']=out['mbsim']
  return response_data

def actionAddcibranches(environ):
  # return current checked examples
  with ConfigFile(True) as config:
    response_data=checkCredicals(environ, config)
    data=json.load(environ['wsgi.input'])
    if response_data['success']:
      # save checked examples
      newcibranch=data['addcibranch']
      curcibranch=config['curcibranch']
      add=True
      for c in curcibranch:
        if c['fmatvec']==newcibranch['fmatvec'] and c['hdf5serie']==newcibranch['hdf5serie'] and \
           c['openmbv']==newcibranch['openmbv'] and c['mbsim']==newcibranch['mbsim']:
          add=False
          break
      if add:
        curcibranch.append(newcibranch)
      # update tobuild
      tobuild=config['tobuild']
      toadd=newcibranch.copy()
      toadd['timestamp']=int(time.time())
      tobuild.append(toadd)
      # response
      response_data['message']='New CI branch combination saved.'
  return response_data

def actionDelcibranches(environ):
  # return current checked examples
  with ConfigFile(True) as config:
    response_data=checkCredicals(environ, config)
    data=json.load(environ['wsgi.input'])
    if response_data['success']:
      # del ci branch
      delcibranch=data['delcibranch']
      newcurcibranch=[]
      for c in config['curcibranch']:
        # never delete master
        if c['fmatvec']=='master' and c['hdf5serie']=='master' and \
           c['openmbv']=='master' and c['mbsim']=='master':
          newcurcibranch.append(c)
        else:
          # do not add the deleted one
          if c['fmatvec']==delcibranch['fmatvec'] and c['hdf5serie']==delcibranch['hdf5serie'] and \
             c['openmbv']==delcibranch['openmbv'] and c['mbsim']==delcibranch['mbsim']:
            continue
          # add others
          newcurcibranch.append(c)
      config['curcibranch']=newcurcibranch
      response_data['message']='CI branch combination deleted.'
  return response_data

def actionGetuser(environ):
  # get user information
  response_data={}
  if 'HTTP_COOKIE' in environ:
    c=http.cookies.SimpleCookie(environ["HTTP_COOKIE"])
    if 'mbsimenvsessionid' in c:
      sessionid=c['mbsimenvsessionid'].value
    else:
      sessionid=None
  else:
    sessionid=None
  if sessionid is None:
    response_data['success']=True
    response_data['username']=None
    response_data['avatar_url']=''
    response_data['message']="No session ID cookie found on your browser."
  else:
    with ConfigFile(False) as config: pass
    if not sessionid in config['session']:
      response_data['success']=True
      response_data['username']=None
      response_data['avatar_url']=''
      response_data['message']="The username of the browser cookie is not known by the server. Please relogin."
    else:
      response_data['success']=True
      response_data['username']=config['session'][sessionid]['name']+" ("+config['session'][sessionid]['login']+")"
      response_data['avatar_url']=config['session'][sessionid]['avatar_url']
      response_data['message']="User information returned."
  return response_data

def actionWebhook(environ):
  # react on web hooks
  response_data={}
  with ConfigFile(True) as config:
    rawdata=environ['wsgi.input'].read()
    sig=environ['HTTP_X_HUB_SIGNATURE'][5:]
    if not hmac.compare_digest(sig, hmac.new(config['webhook_secret'].encode('utf-8'), rawdata, hashlib.sha1).hexdigest()):
      response_data['success']=False
      response_data['message']="Invalid signature. Only github is allowed to send hooks."
    else:
      event=environ['X-GitHub-Event']
      if event=="push":
        data=json.loads(rawdata)
        # we can start the docker container from here but this scripts runs as user apache
        # which does not have access to the docker socket. Hence, we store to the config file and check it with cron.
        # get current config
        curcibranch=config['curcibranch']
        tobuild=config['tobuild']
        if "buildDocker" not in config: config['buildDocker']=[]
        buildDocker=config['buildDocker']
        # get repo and branch from this push
        repo=data['repository']['name']
        if data['ref'][0:11]!="refs/heads/"
          response_data['success']=True
          response_data['message']="This webhook push event is not handled"
          return response_data
        branch=data['ref'][11:]
        # update tobuild
        if repo=="fmatvec" or repo=="hdf5serie" or repo=="openmbv" or repo=="mbsim":
          for c in curcibranch:
            if c[repo]==branch:
              toadd=c.copy()
              toadd['timestamp']=int(time.time())
              tobuild.append(toadd)
        # push to repo "build" -> add to list of docker builds
        if repo=="build" and branch==("staging" if environ["MBSIMENVTAGNAME"]=="staging" else "master"):
          buildDocker.append(data["after"])
        # create response
        response_data['success']=True
        response_data['message']="OK"
      else:
        response_data['success']=True
        response_data['message']="This webhook event type is not handled"
  return response_data

def actionReleasedistribution(environ):
  # copy distribution to release and tag on github
  with ConfigFile(False) as config: pass
  response_data=checkCredicals(environ, config)
  data=json.load(environ['wsgi.input'])
  if response_data['success']:
    # generate tagname, platform and relArchiveName
    tagName=re.sub("mbsim-env-(.*)-shared-build-xxx\..*", "release/"+data['relStr']+"-\\1", data['distArchiveName'])
    platform=re.sub("mbsim-env-(.*)-shared-build-xxx\..*", "\\1", data['distArchiveName'])
    relArchiveName=re.sub("mbsim-env-.*-shared-build-xxx(\..*)", "mbsim-env-release-"+data['relStr']+"-"+platform+"\\1", data['distArchiveName'])
    # access token from config file and standard http header
    c=http.cookies.SimpleCookie(environ["HTTP_COOKIE"])
    if 'mbsimenvsessionid' in c:
      sessionid=c['mbsimenvsessionid'].value
    else:
      sessionid=None
    if sessionid is None:
      response_data['success']=False
      response_data['message']="Not logged in."
    else:
      access_token=config['session'][sessionid]['access_token']
      headers={'Authorization': 'token '+access_token,
               'Accept': 'application/vnd.github.v3+json'}
      # the default response -> is changed/appended later
      response_data['success']=True
      response_data['message']=""
      # the current time -> the create date of the tag object
      curtime=datetime.datetime.utcnow()
      # get user email
      response=requests.get('https://api.github.com/user/emails', headers=headers)
      if response.status_code!=200:
        response_data['success']=False
        response_data['message']="Internal error. Cannot get email address of user."
      else:
        response=response.json()
        # get primary email
        for item in response:
          if item['primary']:
            email=item['email']
        # create tag object, create git reference and create a github release for all repositories
        org="mbsim-env"
        repos=['fmatvec', 'hdf5serie', 'openmbv', 'mbsim']
        # worker function to make github api requests in parallel
        def tagRefRelease(repo, out):
          try:
            # create the git tag object
            createTagData={"tag": tagName,
                           "message": "Release "+data['relStr']+" of MBSim-Env for "+platform+"\n"+\
                                      "\n"+\
                                      "The binary "+platform+" release can be downloaded from\n"+\
                                      "https://"+environ['HTTP_HOST']+"/mbsim/releases/"+relArchiveName+"\n"+\
                                      "Please note that this binary release includes a full build of MBSim-Env not only of this repository.\n"+\
                                      "Also look at https://"+environ['HTTP_HOST']+"/mbsim/releases for other platforms of this release version.\n",
                           "object": data['commitid'][repo],
                           "type": "commit",
                           "tagger": {
                             "name": config['session'][sessionid]['name'],
                             "email": email,
                             "date": curtime.strftime("%Y-%m-%dT%H:%M:%SZ")
                          }}
            response=requestsPost(environ, out, 'https://api.github.com/repos/'+org+'/'+repo+'/git/tags',
                                  headers=headers, dataJson=createTagData)
            # check if the create was successfull
            if response.status_code!=201:
              # not successfull -> set out
              out['success']=False
              out['message']="Unable to create the git tag object for repo "+repo+". Please check the tag status of (at least) this repository manually; "
            else:
              # git tag object created -> get the tag object id
              tagObjectID=response.json()['sha']
              # create the github ref
              createRefData={"ref": "refs/tags/"+tagName,
                             "sha": tagObjectID}
              response=requestsPost(environ, out, 'https://api.github.com/repos/'+org+'/'+repo+'/git/refs',
                                    headers=headers, dataJson=createRefData)
              # check if the create was successfull
              if response.status_code!=201:
                # not successfull -> set out
                out['success']=False
                out['message']="Unable to create the git reference for repo "+repo+". Please check the tag status of (at least) this repository manually; "
              else:
                # git ref object created -> create GitHub release info
                createRelData={"tag_name": tagName,
                               "name": "Release "+data['relStr']+" of MBSim-Env for "+platform,
                               "body": "The binary "+platform+" release can be downloaded from\n"+\
                                       "https://"+environ['HTTP_HOST']+"/mbsim/releases/"+relArchiveName+"\n"+\
                                       "Please note that this binary release includes a full build of MBSim-Env not only of this repository. "+\
                                       "Also look at https://"+environ['HTTP_HOST']+"/mbsim/releases for other platforms of this release version.",
                               "draft": False,
                               "prerelease": False}
                response=requestsPost(environ, out, 'https://api.github.com/repos/'+org+'/'+repo+'/releases',
                                      headers=headers, dataJson=createRelData)
                # check if the update was successfull
                if response.status_code!=201:
                  # not successfull -> set out
                  out['success']=False
                  out['message']="Unable to create the GitHub release info for repo "+repo+". "+\
                                 "Please check the tag/release status of (at least) this repository manually; "
          except:
            # reset all output and generate a json error message
            import traceback
            out.clear()
            out['success']=False
            out['message']="Internal error: Please report the following error to the maintainer:\n"+traceback.format_exc()
        # start worker threads
        thread={}
        out={}
        for repo in repos:
          out[repo]={'success': True, 'message': ''}
          thread[repo]=threading.Thread(target=tagRefRelease, args=(repo, out[repo]))
          thread[repo].start()
        # wait for all threads
        for repo in repos:
          thread[repo].join()
        # combine output of all threads
        for repo in repos:
          if not out[repo]['success']:
            response_data['success']=False
          response_data['message']=response_data['message']+("\n" if len(out[repo]['message'])>0 else "")+out[repo]['message']
        # set message if everything was done Successfully
        if response_data['success']==True:
          response_data['message']="Successfully released and tagged this distribution."+\
                                   ("\n" if len(response_data['message'])>0 else "")+response_data['message']
          # copy the distribution to the release dir
          if not data['reportOutDir'].startswith('/mbsim-report/'):
            response_data['success']=False
            response_data['message']=response_data['message']+" Illegal reportOutDir provided."
          else:
            if data['distArchiveName']=='mbsim-env-win64-shared-build-xxx.zip':
              platformDir="win64-dailyrelease"
            elif data['distArchiveName']=='mbsim-env-linux64-shared-build-xxx.tar.bz2':
              platformDir="linux64-dailyrelease"
            else:
              response_data['success']=False
              response_data['message']=response_data['message']+" Illegal distArchiveName provided."
            if response_data['success']==True:
              srcFile='/var/www/html/mbsim/'+platformDir+'/'+data['reportOutDir'][len('/mbsim-report/'):]+\
                      "/distribute/"+data['distArchiveName']
              dstFile="/var/www/html/mbsim/releases/"+relArchiveName
              shutil.copyfile(srcFile, dstFile)
  return response_data
  
def actionCheckmbsimenvsessionid(environ):
  # check if the session ID provided as POST is authorizised 
  with ConfigFile(False) as config: pass
  data=json.load(environ['wsgi.input'])
  if 'mbsimenvsessionid' in data:
    response_data=checkCredicals(environ, config, data['mbsimenvsessionid'])
  return response_data
  
def actionFiltergithubfeed(environ, start_response):
  import xml.etree.cElementTree as ET
  query=urllib.parse.parse_qs(environ['QUERY_STRING'])
  url=query["url"][0]
  username=query["username"][0]
  response=requests.get(url)
  if response.status_code!=200:
    return {'success': False, 'message': "Cannot get feed"}
  ET.register_namespace("", "http://www.w3.org/2005/Atom")
  root=ET.fromstring(response.content)
  for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
    author=entry.find("{http://www.w3.org/2005/Atom}author")
    if author is None: continue
    name=author.find("{http://www.w3.org/2005/Atom}name")
    if name is None: continue
    if name.text!=username: continue
    root.remove(entry)
  start_response('200 OK', [('Content-type', 'text/xml'),
                            ('Access-Control-Allow-Credentials', 'true')])
  return b'<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root)
