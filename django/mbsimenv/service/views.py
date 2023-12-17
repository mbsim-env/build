import django
import django.contrib.syndication.views
import base
import runexamples
import builds
import service
import json
import threading
import itertools
import hmac
import hashlib
import mbsimenvSecrets
import concurrent.futures
import urllib.parse
import requests
import os
import re
import types
import datetime
from octicons.templatetags.octicons import octicon

# the user profile page
class Home(base.views.Base):
  template_name='service/home.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["buildsystem"]=True
    context['manuals']=service.models.Manual.objects.order_by("manualName")
    if service.models.Info.objects.all().count()==1:
      context['info']=service.models.Info.objects.all()[0]
    context["hostname"]=os.environ.get('MBSIMENVSERVERNAME', 'localhost')
    context["authenticated"]=self.request.user.is_authenticated
    return context

# return the according bootstrap color
def getColor(text):
  if text=="success":
    return "#5cb85c"
  if text=="danger":
    return "#d9534f"
  if text=="warning":
    return "#f0ad4e"
  if text=="secondary":
    return "#777"

# a svg badge with the number of all examples
def currentBuildNrAll(request, buildtype):
  run=builds.models.Run.objects.getCurrent(buildtype, "master", "master", "master", "master")
  if run is None:
    context={"nr": "n/a", "color": getColor("secondary")}
  elif run.endTime is None:
    context={"nr": "...", "color": getColor("secondary")}
  else:
    context={"nr": run.nrAll(), "color": getColor("secondary")}
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the number of failed examples
def currentBuildNrFailed(request, buildtype):
  run=builds.models.Run.objects.getCurrent(buildtype, "master", "master", "master", "master")
  if run is None:
    context={"nr": "n/a", "color": getColor("secondary")}
  elif run.endTime is None:
    context={"nr": "...", "color": getColor("secondary")}
  else:
    nr=run.nrFailed()
    context={"nr": nr, "color": getColor("success" if nr==0 else "danger")}
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the number of all examples
def currentRunexampleNrAll(request, buildtype):
  run=runexamples.models.Run.objects.getCurrent(buildtype, "master", "master", "master", "master")
  if run is None:
    context={"nr": "n/a", "color": getColor("secondary")}
  elif run.endTime is None:
    context={"nr": "...", "color": getColor("secondary")}
  else:
    context={"nr": run.nrAll(), "color": getColor("secondary")}
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the number of failed examples
def currentRunexampleNrFailed(request, buildtype):
  run=runexamples.models.Run.objects.getCurrent(buildtype, "master", "master", "master", "master")
  if run is None:
    context={"nr": "n/a", "color": getColor("secondary")}
  elif run.endTime is None:
    context={"nr": "...", "color": getColor("secondary")}
  else:
    nr=run.nrFailed()
    context={"nr": nr, "color": getColor("success" if nr==0 else "danger")}
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the coverage rate
def currentCoverageRate(request, buildtype):
  run=runexamples.models.Run.objects.getCurrent(buildtype, "master", "master", "master", "master")
  if run is None:
    context={"nr": "n/a", "color": getColor("secondary")}
  elif run.endTime is None:
    context={"nr": "...", "color": getColor("secondary")}
  elif run.coverageOK==False:
    context={"nr": "ERR", "color": getColor("danger")}
  else:
    context={
      "nr": str(int(round(run.coverageRate)))+"%",
      "color": getColor("danger" if run.coverageRate<70 else ("warning" if run.coverageRate<90 else "success")),
    }
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# site for branch combinations
class EditBranches(base.views.Base):
  template_name='service/editbranches.html'

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["buildsystem"]=True

    # just a list which can be used to loop over in the template
    context['repoList']=["fmatvec", "hdf5serie", "openmbv", "mbsim"]
    context['model']=kwargs["model"]
    context['modelHuman']="continuous integration" if context["model"]=="CIBranches" else "daily"
    return context

# response to ajax requests of the edit branches datatable
class DataTableEditBranches(base.views.DataTable):
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.model=kwargs["model"]

  # return the queryset to display [required]
  def queryset(self):
    return getattr(service.models, self.model).objects.order_by("fmatvecBranch", "hdf5serieBranch", "openmbvBranch", "mbsimBranch")

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "fmatvecBranch"

  def colData_remove(self, ds):
    tooltip="service/%s: id=%d"%(self.model, ds.id)
    return base.helper.tooltip(\
      '<button class="btn btn-secondary btn-xs" onclick="deleteBranchCombination($(this), \'{}\');" type="button">{}</button>'.\
      format(django.urls.reverse('service:db_deletebranchcombi', args=[self.model, ds.id]), octicon("diff-removed")), tooltip)

  def colData_fmatvecBranch(self, ds):
    return '<a href="https://github.com/mbsim-env/fmatvec/tree/'+ds.fmatvecBranch+'">'\
           '<span class="badge badge-primary">'+octicon("git-branch")+'&nbsp;'+ds.fmatvecBranch+'</span></a>'

  def colData_hdf5serieBranch(self, ds):
    return '<a href="https://github.com/mbsim-env/hdf5serie/tree/'+ds.hdf5serieBranch+'">'\
           '<span class="badge badge-primary">'+octicon("git-branch")+'&nbsp;'+ds.hdf5serieBranch+'</span></a>'

  def colData_openmbvBranch(self, ds):
    return '<a href="https://github.com/mbsim-env/openmbv/tree/'+ds.openmbvBranch+'">'\
           '<span class="badge badge-primary">'+octicon("git-branch")+'&nbsp;'+ds.openmbvBranch+'</span></a>'

  def colData_mbsimBranch(self, ds):
    return '<a href="https://github.com/mbsim-env/mbsim/tree/'+ds.mbsimBranch+'">'\
           '<span class="badge badge-primary">'+octicon("git-branch")+'&nbsp;'+ds.mbsimBranch+'</span></a>'

# response to ajax requests -> output repository branches
def repoBranches(request):
  # prepare the cache for github access
  gh=base.helper.GithubCache(request)

  repoList=["fmatvec", "hdf5serie", "openmbv", "mbsim"]
  res={}
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout):
    # not logged in or allowed -> just show this as branch names and do not enable the comboxboxes and buttons
    for repo in repoList:
      res[repo+"Branch"]=["&lt;not logged in or allowed&gt;"]
    res["enable"]=False
  else:
    # logged in and allowed
    lock=threading.Lock()
    def getBranchesWorker(repo):
      return (repo+"Branch", list(map(lambda b: b.name, gh.getMbsimenvRepoBranches(repo, lock))))
    exe=concurrent.futures.ThreadPoolExecutor(max_workers=len(repoList))
    res=dict(exe.map(getBranchesWorker, repoList))
    res["enable"]=True
  return django.http.JsonResponse(res, json_dumps_params={"indent": 2})

# return all current branch combinations as json
def getBranchCombination(request, model):
  res=[]
  for b in getattr(service.models, model).objects.all():
    res.append({"id": b.id,
                "fmatvecBranch": b.fmatvecBranch,
                "hdf5serieBranch": b.hdf5serieBranch,
                "openmbvBranch": b.openmbvBranch,
                "mbsimBranch": b.mbsimBranch})
  return django.http.JsonResponse({"data": res}, json_dumps_params={"indent": 2})

# response to ajax request to add a new branch combination
def addBranchCombination(request, model):
  # prepare the cache for github access
  gh=base.helper.GithubCache(request)
  # if not logged in or not the appropriate right then return a http error
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout):
    return django.http.HttpResponseForbidden()
  # get the request data as json
  req=json.loads(request.body)
  if req["fmatvecBranch"]=="" or req["hdf5serieBranch"]=="" or req["openmbvBranch"]=="" or req["mbsimBranch"]=="":
    return django.http.HttpResponseBadRequest("At least one branch name is empty.")
  # create branches table entry
  b=getattr(service.models, model)()
  b.fmatvecBranch=req["fmatvecBranch"]
  b.hdf5serieBranch=req["hdf5serieBranch"]
  b.openmbvBranch=req["openmbvBranch"]
  b.mbsimBranch=req["mbsimBranch"]
  # save it
  try:
    b.save()
  except django.db.utils.IntegrityError:
    return django.http.HttpResponseBadRequest("This branch combination is not allowed (already exists).")
  # for ci branch trigger the build now
  if model=="CIBranches":
    # executor: MBSim-Env
    recTime=django.utils.timezone.now()
    ciq, _=service.models.CIQueue.objects.get_or_create(fmatvecBranch=req["fmatvecBranch"],
                                                        hdf5serieBranch=req["hdf5serieBranch"],
                                                        openmbvBranch=req["openmbvBranch"],
                                                        mbsimBranch=req["mbsimBranch"],
                                                        defaults={"recTime": recTime})
    ciq.recTime=recTime
    ciq.save()
    # executor: Github Actions
    data={"event_type": "branchCombiAdded",
          "client_payload":
            {"model": model,
             "branches":
               {"id": b.id,
                "fmatvecBranch": b.fmatvecBranch,
                "hdf5serieBranch": b.hdf5serieBranch,
                "openmbvBranch": b.openmbvBranch,
                "mbsimBranch": b.mbsimBranch,
         }  }  }
    response=requests.post("https://api.github.com/repos/mbsim-env/build/dispatches", json=data,
                           headers={"Authorization": "token "+mbsimenvSecrets.getSecrets("githubAccessToken")})
    if response.status_code!=204:
      return django.http.HttpResponseBadRequest("Branch combination added but failed to trigger the Github Actions workflow."+\
                                                (response.content.decode("utf-8") if django.conf.settings.DEBUG else ""))
  return django.http.HttpResponse()

# response to ajax request to delete a branch combination
def deleteBranchCombination(request, model, id):
  # prepare the cache for github access
  gh=base.helper.GithubCache(request)
  # if not logged in or not the appropriate right then return a http error
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout):
    return django.http.HttpResponseForbidden()
  # get branch combi in table the example on the the reference should be updated or create it
  b=getattr(service.models, model).objects.get(id=id)
  b.delete()
  return django.http.HttpResponse()

# improve portability of Feed: use "Z" as timezone instead of "+01:00" as many feed readers do not understand "+01:00"
class MyAtom1Feed(django.utils.feedgenerator.Atom1Feed):
  def _override(self, handler):
    if not hasattr(handler, "addQuickElement_org"):
      setattr(handler, "addQuickElement_org", handler.addQuickElement)
      def myAddQuickElement(self, name, contents=None, attrs=None):
        if name=="updated" or name=="published":
          contents=contents[0:-3]+contents[-2:]
          try:
            dt=datetime.datetime.strptime(contents, "%Y-%m-%dT%H:%M:%S.%f%z") # try with .%f ...
          except ValueError:
            dt=datetime.datetime.strptime(contents, "%Y-%m-%dT%H:%M:%S%z") # and, if not working without .%f
          dt=(dt+dt.utcoffset()).replace(microsecond=0, tzinfo=None)
          contents=dt.isoformat()+"Z"
        self.addQuickElement_org(name, contents, attrs)
      handler.addQuickElement=types.MethodType(myAddQuickElement, handler)
  def add_root_elements(self, handler):
    self._override(handler)
    super().add_root_elements(handler)
  def add_item_elements(self, handler, item):
    self._override(handler)
    super().add_item_elements(handler, item)

html2text=re.compile("<[^>]*>")
class Feed(django.contrib.syndication.views.Feed):
  feed_type=MyAtom1Feed
  title="MBSim-Env Build System Feeds"
  subtitle="Failed builds and examples of the MBSim-Environment build system."
  link=django.urls.reverse_lazy("service:home")

  # return a iterator for all items of the feed
  def items(self):
    date=django.utils.timezone.now()-django.utils.timezone.timedelta(days=30)
    # get builds and examples newer than 30days
    buildTypes=["linux64-ci", "win64-ci", "linux64-dailydebug", "linux64-dailydebug-valgrind", "linux64-dailyrelease", "win64-dailyrelease"]
    buildRun=builds.models.Run.objects.filterFailed().filter(endTime__gt=date, buildType__in=buildTypes)
    exampleRun=runexamples.models.Run.objects.filterFailed().filter(endTime__gt=date, buildType__in=buildTypes)
    # merge both lists and sort by endTime
    return sorted(itertools.chain(buildRun, exampleRun), key=lambda x: x.endTime, reverse=True)
  
  # reutrn feed entry title, description, link and pubdate
  def item_title(self, run):
    isBuild=type(run) is builds.models.Run
    buildRun=run if isBuild else run.build_run
    executor=" ("+html2text.sub("", buildRun.executor)+")" if buildRun is not None else ""
    return ("Build" if isBuild else "Examples")+" failed: "+run.buildType+executor
  def item_description(self, run):
    isBuild=type(run) is builds.models.Run
    buildRun=run if isBuild else run.build_run
    if buildRun is None:
      return f'''<p><b>{run.nrFailed()} of {run.nrAll()} {"build parts" if isBuild else "examples"} failed.</b></p>'''
    def bolds(bold):
      return '<b>' if bold else ""
    def bolde(bold):
      return '</b>' if bold else ""
    ret = f'''<p><b>{run.nrFailed()} of {run.nrAll()} {"build parts" if isBuild else "examples"} failed.</b></p>
              <p>Build was run on: {buildRun.executor}</p>
              <p>Build done with the following branches:</p>
              <dl>'''
    for repo in buildRun.repos.all():
      ret +=f'''<dt>{bolds(repo.triggered)}fmatvec{bolde(repo.triggered)}</dt>+\
                <dd><b>{repo.branch}</b>: <i>{repo.updateAuthor}</i> - {repo.updateMsg}</dd>'''
    ret +=f'''</dl>'''
    return ret
  def item_link(self, run):
    isBuild=type(run) is builds.models.Run
    return django.urls.reverse("builds:run" if isBuild else "runexamples:run", args=[run.id])
  def item_pubdate(self, run):
    return run.endTime
  def item_updateddate(self, run):
    return run.endTime
  def item_enclosures(self, run):
    isBuild=type(run) is builds.models.Run
    OCTICON="gear" if isBuild else "beaker"
    return [django.utils.feedgenerator.Enclosure(
      "https://"+os.environ['MBSIMENVSERVERNAME']+django.conf.settings.STATIC_URL+"octiconpng/"+OCTICON+".png",
      "0", "image/png")]
  def item_author_name(self, run):
    return "MBSim-Env"

# site for release download
class Releases(base.views.Base):
  template_name='service/releases.html'

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["download"]=True

    currentReleases=[]
    olderReleases=[]
    allReleases=service.models.Release.objects.order_by('-versionMajor', '-versionMinor')
    if allReleases:
      currentVersionMajor=allReleases[0].versionMajor
      currentVersionMinor=allReleases[0].versionMinor
      currentReleases=allReleases.filter(versionMajor=currentVersionMajor, versionMinor=currentVersionMinor)
      olderReleases=allReleases.exclude(versionMajor=currentVersionMajor, versionMinor=currentVersionMinor)

    # just a list which can be used to loop over in the template
    context['currentReleases']=currentReleases
    context['olderReleases']=olderReleases
    return context

def releaseFile(request, filename):
  r=service.models.Release.objects.filter(releaseFile__endswith=filename).first()
  if r is not None:
    ff=r.releaseFile
  else:
    r=service.models.Release.objects.filter(releaseDebugFile__endswith=filename).first()
    if r is not None:
      ff=r.releaseDebugFile
    else:
      return django.http.HttpResponseBadRequest("Release file not found.")
  return django.http.FileResponse(ff, as_attachment=True, filename=filename)
def currentReleaseFile(request, platform):
  r=service.models.Release.objects.filter(platform=platform).order_by('-versionMajor', '-versionMinor').first()
  return django.http.FileResponse(r.releaseFile, as_attachment=True, filename=r.releaseFileName)
def currentReleaseDebugFile(request, platform):
  r=service.models.Release.objects.filter(platform=platform).order_by('-versionMajor', '-versionMinor').first()
  return django.http.FileResponse(r.releaseDebugFile, as_attachment=True, filename=r.releaseDebugFileName)

# a svg badge with the number manuals
def manualsNrAll(request):
  nr=service.models.Manual.objects.all().count()
  context={
    "nr": nr,
    "color": getColor("secondary"),
  }
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the number of failed manuals
def manualsNrFailed(request):
  nr=service.models.Manual.objects.filterFailed().count()
  context={
    "nr": nr,
    "color": getColor("success" if nr==0 else "danger"),
  }
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# response to a GitHub webhook
# disable CSRF for this URL, we check the github webhook signature to keep it secure
@django.views.decorators.csrf.csrf_exempt
def webhook(request):
  rawdata=request.body
  sig=request.headers['X_HUB_SIGNATURE'][5:]
  try:
    if not hmac.compare_digest(sig, hmac.new(mbsimenvSecrets.getSecrets("githubWebhookSecret").encode('utf-8'), rawdata, hashlib.sha1).hexdigest()):
      return django.http.HttpResponseForbidden()
  except:
    if django.conf.settings.DEBUG:
      raise
    else:
      raise RuntimeError("Original exception avoided in webhook to ensure that no secret is printed.") from None
  event=request.headers['X-GitHub-Event']
  res={"event": event}
  if event=="push":
    # get repo, branch and commit from this push
    data=json.loads(rawdata)
    res["repo"]=data['repository']['name']
    if data['ref'][0:11]!="refs/heads/":
      return django.http.HttpResponseBadRequest("Illegal data in 'ref'.")
    res["branch"]=data['ref'][11:]
    if data["head_commit"] is None:
      return django.http.HttpResponseBadRequest("No new commit at current head of 'ref'.")
    res["commitID"]=data["head_commit"]["id"]
    if res["repo"]=="fmatvec" or res["repo"]=="hdf5serie" or res["repo"]=="openmbv" or res["repo"]=="mbsim":
      res["addedBranchCombinations"]=[]

      # executor: MBSim-Env

      # get all branch combinations to build as save in queue
      masterRecTime=django.utils.timezone.now() # we push the master/master/master/master branch combi first
      empty=True
      for bc in service.models.CIBranches.objects.filter(**{res["repo"]+"Branch": res["branch"]}):
        empty=False
        branchCombination={
          "fmatvecBranch": bc.fmatvecBranch,
          "hdf5serieBranch": bc.hdf5serieBranch,
          "openmbvBranch": bc.openmbvBranch,
          "mbsimBranch": bc.mbsimBranch,
        }
        if bc.fmatvecBranch=="master" and bc.hdf5serieBranch=="master" and bc.openmbvBranch=="master" and bc.mbsimBranch=="master":
          recTime=masterRecTime
        else:
          recTime=django.utils.timezone.now()
        ciq, _=service.models.CIQueue.objects.get_or_create(**branchCombination, defaults={"recTime": recTime})
        ciq.recTime=recTime
        ciq.save()
        res["addedBranchCombinations"].append(branchCombination)
      if empty: # branch not found in branch combinations -> build this branch with master of all other branches
        branchCombination={
          "fmatvecBranch": "master",
          "hdf5serieBranch": "master",
          "openmbvBranch": "master",
          "mbsimBranch": "master",
        }
        branchCombination[res["repo"]+"Branch"]=res["branch"]
        recTime=django.utils.timezone.now()
        ciq, _=service.models.CIQueue.objects.get_or_create(**branchCombination, defaults={"recTime": recTime})
        ciq.recTime=recTime
        ciq.save()
        res["addedBranchCombinations"].append(branchCombination)

      # executor: Github Actions

      data={"event_type": "ci",
            "client_payload":
              {"repository": "mbsim-env/"+res["repo"],
               "ref_name": res["branch"],
               "sha": res["commitID"]}
           }
      response=requests.post("https://api.github.com/repos/mbsim-env/build/dispatches", json=data,
                             headers={"Authorization": "token "+mbsimenvSecrets.getSecrets("githubAccessToken")})
      if response.status_code!=204:
        return django.http.HttpResponseBadRequest("Faild to dispatch to mbsim-env/build Github Actions workflow."+\
                                                  (response.content.decode("utf-8") if django.conf.settings.DEBUG else ""))
      # just some messages
      res["githubAction"]={"target": "mbsim-env/build", "data": data}

    elif res["repo"]=="build":
      if res["branch"]=="staging":
        ciq=service.models.CIQueue()
        ciq.buildCommitID=res["commitID"]
        ciq.recTime=django.utils.timezone.now()
        ciq.save()
        res["addedBuildCommitID"]=res["commitID"]
      else:
        res["skipNoneStagingBranch"]=res["commitID"]
    else:
      return django.http.HttpResponseBadRequest("Unknown repo.")
    return django.http.JsonResponse(res, json_dumps_params={"indent": 2})
  else:
    return django.http.HttpResponseBadRequest("Unhandled webhook event.")

class Webapp(base.views.Base):
  template_name='service/webapp.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["buildsystem"]=True
    context["prog"]=self.request.GET["prog"]
    context["buildRunID"]=self.request.GET["buildRunID"]
    context["exampleName"]=self.request.GET["exampleName"]
    # we can only pass additonal information to websockify via a token query. we use a url quoted json string as token
    context["token"]=urllib.parse.quote_plus(json.dumps(self.request.GET))
    return context

def checkValidUser(request):
  # prepare the cache for github access
  gh=base.helper.GithubCache(request)
  # if not logged in or not the appropriate right then return a http error
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout) and not base.helper.isLocalUser(request):
    return django.http.HttpResponseForbidden()
  return django.http.HttpResponse()

# this URL need a query string of the format ?url=URL&username=USERNAME
# It gets the atom github feed from the url URL and removes every entries which have "author" set to USERNAME.
# This filtered atom feed is retunred than.
# (Use it e.g. to filter out your own commits from your personal github feed)
def filterGithubFeed(request):
  import xml.etree.cElementTree as ET
  # get query data
  url=request.GET["url"]
  username=request.GET["username"]
  # get original feed
  response=requests.get(url)
  if response.status_code!=200:
    return django.http.HttpResponseBadRequest("Cannot get feed from github.")
  # create filtered feed
  ET.register_namespace("", "http://www.w3.org/2005/Atom")
  root=ET.fromstring(response.content)
  for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
    author=entry.find("{http://www.w3.org/2005/Atom}author")
    if author is None: continue
    name=author.find("{http://www.w3.org/2005/Atom}name")
    if name is None: continue
    if name.text!=username: continue
    root.remove(entry)
  return django.http.HttpResponse(b'<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root), content_type="text/xml")

# the user profile page
class CreateFilterGitHubFeed(base.views.Base):
  template_name='service/createfiltergithubfeed.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["buildsystem"]=True
    context["hostname"]=os.environ.get('MBSIMENVSERVERNAME', 'localhost')
    return context

class LatestBranchCombiBuilds(base.views.Base):
  template_name='service/latestbranchcombibuilds.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["buildsystem"]=True
    context['model']=kwargs["model"]
    context['modelHuman']="continuous integration" if context["model"]=="CIBranches" else "daily"
    return context

class DataTableLatestBranchCombiBuilds(base.views.DataTable):
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.model=kwargs["model"]

  # return the queryset to display [required]
  def queryset(self):
    if self.model=="CIBranches":
      return builds.models.Run.objects.filter(buildType__endswith="-ci")
    elif self.model=="DailyBranches":
      return builds.models.Run.objects.exclude(buildType__endswith="-ci")
    else:
      return None

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "buildType"

  def colData_timedate_buildType_executor(self, ds):
    import humanize
    return octicon("clock")+'&nbsp;'+base.helper.tooltip(humanize.naturaldelta(django.utils.timezone.now()-ds.startTime)+"&nbsp;ago",
                               ds.startTime.isoformat()+"&#013;builds/Run: id="+str(ds.id))+'<br/>'+\
           base.helper.buildTypeIcon(ds.buildType)+'&nbsp;'+ds.buildType+'<br/>'+\
           octicon("terminal")+'&nbsp;'+ds.executor
  def colSortKey_timedate_buildType_executor(self, ds):
    return ds.startTime.isoformat()

  def _colData_Branch(self, ds, repo):
    import humanize
    return '''<nobr>
                <a href="https://github.com/mbsim-env/{REPO}/tree/{BRANCH}">
                  <span class="badge badge-primary">{OCTICONBRANCH}&nbsp;{BRANCH}</span>
                </a>
                <a href="https://github.com/mbsim-env/{REPO}/commit/{COMMITID}">
                  {OCTICONCOMMIT}{COMMITIDSHORT}…
                </a>
              </nobr><br/>
              <nobr>
                {OCTICONPERSON}&nbsp;<i>{AUTHOR}</i>
              </nobr><br/>
              <nobr>
                {DATE_WITHTOOLTIP}
              </nobr><br/>
              {MSG}'''.\
           format(REPO=repo, BRANCH=getattr(ds, repo+"Branch"),
                  OCTICONBRANCH=octicon("git-branch"), OCTICONCOMMIT=octicon("git-commit"),
                  COMMITID=getattr(ds, repo+"UpdateCommitID"), COMMITIDSHORT=getattr(ds, repo+"UpdateCommitID")[0:7],
                  MSG=getattr(ds, repo+"UpdateMsg"), OCTICONPERSON=octicon("person"), AUTHOR=getattr(ds, repo+"UpdateAuthor"),
                  OCTICONCLOCK=octicon("clock"),
                  DATE_WITHTOOLTIP=base.helper.tooltip(octicon("clock")+"&nbsp;"+humanize.naturaldelta(
                    django.utils.timezone.now()-getattr(ds, repo+"UpdateDate"))+" ago",
                    getattr(ds, repo+"UpdateDate").isoformat()
                  ) if getattr(ds, repo+"UpdateDate") is not None else "" \
                 )
  def colData_fmatvecBranch(self, ds):
    return self._colData_Branch(ds, "fmatvec")
  def colData_hdf5serieBranch(self, ds):
    return self._colData_Branch(ds, "hdf5serie")
  def colData_openmbvBranch(self, ds):
    return self._colData_Branch(ds, "openmbv")
  def colData_mbsimBranch(self, ds):
    return self._colData_Branch(ds, "mbsim")

  def _colClass_Branch(self, ds, repo):
    return "table-info" if getattr(ds, repo+"Triggered") else ""
  def colClass_fmatvecBranch(self, ds):
    return self._colClass_Branch(ds, "fmatvec")
  def colClass_hdf5serieBranch(self, ds):
    return self._colClass_Branch(ds, "hdf5serie")
  def colClass_openmbvBranch(self, ds):
    return self._colClass_Branch(ds, "openmbv")
  def colClass_mbsimBranch(self, ds):
    return self._colClass_Branch(ds, "mbsim")

  def colData_buildStatus_exampleStatus(self, ds):
    buildFinished=ds.endTime is not None
    data='''<a href="{URL}">
              <span class="badge badge-{COLOR}">{NRFAILED}</span>/<span class="badge badge-secondary">{NRALL}</span>
            </a>'''.format(
         URL=django.urls.reverse("builds:run", args=[ds.id]),
         COLOR=("success" if ds.nrFailed()==0 else "danger") if buildFinished else "secondary",
         NRFAILED=ds.nrFailed() if buildFinished else "...", NRALL=ds.nrAll() if buildFinished else "...")
    data='<nobr>'+octicon("gear")+' '+data+'</nobr><br/>'
    nrAll=0
    nrFailed=0
    count=0
    exid=None
    examplesFinished=True
    for ex in ds.examples.all():
      if exid is None: exid=ex.id
      count+=1
      nrAll+=ex.nrAll()
      nrFailed+=ex.nrFailed()
      if examplesFinished: examplesFinished=ex.endTime is not None
    if count>0:
      d='''<a href="{URL}">
             <span class="badge badge-{COLOR}">{NRFAILED}</span>/<span class="badge badge-secondary">{NRALL}</span>
           </a>'''.format(
        URL=django.urls.reverse("runexamples:run", args=[exid]) if count==1 else \
            django.urls.reverse("builds:run", args=[ds.id])+"#EXAMPLES",
        COLOR=("success" if nrFailed==0 else "danger") if examplesFinished else "secondary",
        NRFAILED=nrFailed if examplesFinished else "...", NRALL=nrAll if examplesFinished else "...")
      data+='<nobr>'+octicon("beaker")+' '+d+'</nobr>'
    return data
  def colClass_buildStatus_exampleStatus(self, ds):
    buildFinished=ds.endTime is not None
    examplesFailed=False
    examplesFinished=True
    for ex in ds.examples.all():
      if examplesFinished: examplesFinished=ex.endTime is not None
      if ex.nrFailed()>0:
        examplesFailed=True
        break
    return "table-danger" if examplesFailed or ds.nrFailed()>0 else \
           ("table-success" if buildFinished and examplesFinished else "table-wanring")

class Docu(base.views.Base):
  template_name='service/docu.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["docu"]=True
    context['manualsSecondary']=service.models.Manual.objects.exclude(manualName="mbsimgui_first_steps")
    return context
