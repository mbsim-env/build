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
from octicons.templatetags.octicons import octicon

# the user profile page
class Home(base.views.Base):
  template_name='service/home.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context['manuals']=service.models.Manual.objects.all()
    if service.models.Info.objects.all().count()==1:
      context['info']=service.models.Info.objects.all()[0]
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
  run=builds.models.Run.objects.getCurrent(buildtype)
  if run is None:
    context={"nr": "n/a", "color": getColor("secondary")}
  elif run.endTime is None:
    context={"nr": "...", "color": getColor("secondary")}
  else:
    context={"nr": run.nrAll(), "color": getColor("secondary")}
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the number of failed examples
def currentBuildNrFailed(request, buildtype):
  run=builds.models.Run.objects.getCurrent(buildtype)
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
  run=runexamples.models.Run.objects.getCurrent(buildtype)
  if run is None:
    context={"nr": "n/a", "color": getColor("secondary")}
  elif run.endTime is None:
    context={"nr": "...", "color": getColor("secondary")}
  else:
    context={"nr": run.nrAll(), "color": getColor("secondary")}
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the number of failed examples
def currentRunexampleNrFailed(request, buildtype):
  run=runexamples.models.Run.objects.getCurrent(buildtype)
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
  run=runexamples.models.Run.objects.getCurrent(buildtype)
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
    return getattr(service.models, self.model).objects.all()

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "fmatvecBranch"

  def colData_remove(self, ds):
    tooltip="service/%s: id=%d"%(self.model, ds.id)
    if ds.fmatvecBranch=="master" and ds.hdf5serieBranch=="master" and ds.openmbvBranch=="master" and ds.mbsimBranch=="master":
      return base.helper.tooltip("not removeable", tooltip)
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
  return django.http.JsonResponse(res)

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
  if b.fmatvecBranch=="master" and b.hdf5serieBranch=="master" and \
     b.openmbvBranch=="master" and b.mbsimBranch=="master":
    return django.http.HttpResponseBadRequest("This branch combination cannot be deleted.")
  b.delete()
  return django.http.HttpResponse()

class Feed(django.contrib.syndication.views.Feed):
  title="MBSim-Env Build System Feeds"
  description="Fail builds and examples of the MBSim-Environment build system."
  link=django.urls.reverse_lazy("service:home")

  # return a iterator for all items of the feed
  def items(self):
    date=django.utils.timezone.now()-django.utils.timezone.timedelta(days=30)
    # get builds and examples newer than 30days
    buildRun=builds.models.Run.objects.filterFailed().filter(startTime__gt=date)
    exampleRun=runexamples.models.Run.objects.filterFailed().filter(startTime__gt=date)
    # merge both lists and sort by startTime
    return sorted(itertools.chain(buildRun, exampleRun), key=lambda x: x.startTime, reverse=True)
  
  # reutrn feed entry title, description, link and pubdate
  def item_title(self, run):
    return ("Build" if type(run) is builds.models.Run else "Examples")+" failed: "+run.buildType
  def item_description(self, run):
    return "{} of {} {} failed.".format(run.nrFailed(), run.nrAll(), "build parts" if type(run) is builds.models.Run else "examples")
  def item_link(self, run):
    return django.urls.reverse("builds:run" if type(run) is builds.models.Run else "runexamples:run", args=[run.id])
  def item_pubdate(self, run):
    return run.startTime

# site for release download
class Releases(base.views.Base):
  template_name='service/releases.html'

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)

    allReleases=service.models.Release.objects.order_by('-versionMajor', '-versionMinor')
    currentVersionMajor=allReleases[0].versionMajor
    currentVersionMinor=allReleases[0].versionMinor
    currentReleases=allReleases.filter(versionMajor=currentVersionMajor, versionMinor=currentVersionMinor)
    olderReleases=allReleases.exclude(versionMajor=currentVersionMajor, versionMinor=currentVersionMinor)

    # just a list which can be used to loop over in the template
    context['currentReleases']=currentReleases
    context['olderReleases']=olderReleases
    return context

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
  if not hmac.compare_digest(sig, hmac.new(mbsimenvSecrets.getSecrets()["githubWebhookSecret"].encode('utf-8'), rawdata, hashlib.sha1).hexdigest()):
    return django.http.HttpResponseForbidden()
  event=request.headers['X-GitHub-Event']
  res={"event": event}
  if event=="push":
    # get repo, branch and commit from this push
    data=json.loads(rawdata)
    res["repo"]=data['repository']['name']
    if data['ref'][0:11]!="refs/heads/":
      return django.http.HttpResponseBadRequest("Illegal data in 'ref'.")
    res["branch"]=data['ref'][11:]
    res["commitID"]=data["after"]
    if res["repo"]=="fmatvec" or res["repo"]=="hdf5serie" or res["repo"]=="openmbv" or res["repo"]=="mbsim":
      res["addedBranchCombinations"]=[]
      # get all branch combinations to build as save in queue
      masterRecTime=django.utils.timezone.now() # we push the master/master/master/master branch combi first
      for bc in service.models.CIBranches.objects.filter(**{res["repo"]+"Branch": res["branch"]}):
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
    elif res["repo"]=="build":
      ciq=service.models.CIQueue()
      ciq.buildCommitID=res["commitID"]
      ciq.recTime=django.utils.timezone.now()
      ciq.save()
      res["addedBuildCommitID"]=res["commitID"]
    else:
      return django.http.HttpResponseBadRequest("Unknown repo.")
    return django.http.JsonResponse(res)
  else:
    return django.http.HttpResponseBadRequest("Unhandled webhook event.")

class Webapp(base.views.Base):
  template_name='service/webapp.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["prog"]=kwargs["prog"]
    context["buildType"]=kwargs["buildType"]
    context["exampleName"]=kwargs["exampleName"]
    # we can only pass additonal information to websockify via a token query. we use a url quoted json string as token
    context["token"]=urllib.parse.quote_plus(json.dumps({
      "prog": kwargs["prog"], "buildType": kwargs["buildType"], "exampleName": kwargs["exampleName"]
    }))
    return context

def checkValidUser(request):
  # prepare the cache for github access
  gh=base.helper.GithubCache(request)
  # if not logged in or not the appropriate right then return a http error
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout):
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
