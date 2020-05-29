import django
import django.contrib.syndication.views
import base
import runexamples
import builds
import service
import json
import threading
import itertools
import concurrent.futures
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
  nr=run.nrAll() if run else 0
  context={
    "nr": nr,
    "color": getColor("secondary"),
  }
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the number of failed examples
def currentBuildNrFailed(request, buildtype):
  run=builds.models.Run.objects.getCurrent(buildtype)
  nr=run.nrFailed() if run else 0
  context={
    "nr": nr,
    "color": getColor("success" if nr==0 else "danger"),
  }
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the number of all examples
def currentRunexampleNrAll(request, buildtype):
  run=runexamples.models.Run.objects.getCurrent(buildtype)
  nr=run.nrAll() if run else 0
  context={
    "nr": nr,
    "color": getColor("secondary"),
  }
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the number of failed examples
def currentRunexampleNrFailed(request, buildtype):
  run=runexamples.models.Run.objects.getCurrent(buildtype)
  nr=run.nrFailed() if run else 0
  context={
    "nr": nr,
    "color": getColor("success" if nr==0 else "danger"),
  }
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# a svg badge with the coverage rate
def currentCoverageRate(request, buildtype):
  run=runexamples.models.Run.objects.getCurrent(buildtype)
  if run is None or run.coverageOK==False:
    context={
      "nr": "ERR",
      "color": getColor("danger"),
    }
  else:
    context={
      "nr": str(int(round(run.coverageRate)))+"%",
      "color": getColor("danger" if run.coverageRate<70 else ("warning" if run.coverageRate<90 else "success")),
    }
  return django.shortcuts.render(request, 'service/nrbadge.svg', context, content_type="image/svg+xml")

# site for ci branch combinations
class CIBranches(base.views.Base):
  template_name='service/cibranches.html'

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)

    # just a list which can be used to loop over in the template
    context['repoList']=["fmatvec", "hdf5serie", "openmbv", "mbsim"]
    return context

# response to ajax requests of the CI branches datatable
class DataTableCIBranches(base.views.DataTable):
  # return the queryset to display [required]
  def queryset(self):
    return service.models.CIBranches.objects.all()

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "fmatvecBranch"

  def colData_remove(self, ds):
    if ds.fmatvecBranch=="master" and ds.hdf5serieBranch=="master" and ds.openmbvBranch=="master" and ds.mbsimBranch=="master":
      return ""
    return '<button class="btn btn-secondary btn-xs" onclick="deleteBranchCombination($(this), \'{}\');" type="button">{}</button>'.\
           format(django.urls.reverse('service:db_deletebranchcombi', args=[ds.id]), octicon("diff-removed"))

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
def addBranchCombination(request):
  # prepare the cache for github access
  gh=base.helper.GithubCache(request)
  # if not logged in or not the appropriate right then return a http error
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout):
    return django.http.HttpResponseForbidden()
  # get the request data as json
  req=json.loads(request.body)
  if req["fmatvecBranch"]=="" or req["hdf5serieBranch"]=="" or req["openmbvBranch"]=="" or req["mbsimBranch"]=="":
    return django.http.HttpResponseBadRequest("At least one branch name is empty.")
  # create CIBranches table entry
  b=service.models.CIBranches()
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
def deleteBranchCombination(request, id):
  # prepare the cache for github access
  gh=base.helper.GithubCache(request)
  # if not logged in or not the appropriate right then return a http error
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout):
    return django.http.HttpResponseForbidden()
  # get branch combi in table the example on the the reference should be updated or create it
  b=service.models.CIBranches.objects.get(id=id)
  if b.fmatvecBranch=="master" and b.hdf5serieBranch=="master" and \
     b.openmbvBranch=="master" and b.mbsimBranch=="master":
    return django.http.HttpResponseBadRequest("This branch combination cannot be deleted.")
  b.delete()
  return django.http.HttpResponse()

class Feed(django.contrib.syndication.views.Feed):
  title="MBSim-Env Build System Feeds"
  description="Fail builds and examples of the MBSim-Environment build system."
  def link(self):
    # cannot be a attribute of this class because django.urls.reverse is not possible their
    return django.urls.reverse("service:home")

  # return a iterator for all items of the feed
  def items(self):
    now=django.utils.timezone.now()
    # show only build builds/examples from the last 30days
    delta=django.utils.timezone.timedelta(days=30)
    # generator function for builds
    def buildGen(runs):
      for run in runs:
        if run.startTime<now-delta: continue
        nrFailed=run.nrFailed()
        if nrFailed==0: continue
        yield {
          "title": "Build Failed: "+run.buildType,
          "desc": "{} of {} build parts failed.".format(nrFailed, run.nrAll()),
          "link": django.urls.reverse("builds:run", args=[run.id]),
          "pubdate": run.startTime,
        }
    genBuilds=buildGen(builds.models.Run.objects.all())
    # generator function for runexamples
    def exampleRunGen(runs):
      for run in runs:
        if run.startTime<now-delta: continue
        nrFailed=run.nrFailed()
        if nrFailed==0: continue
        yield {
          "title": "Examples Failed: "+run.buildType,
          "desc": "{} of {} examples failed.".format(nrFailed, run.nrAll()),
          "link": django.urls.reverse("runexamples:run", args=[run.id]),
          "pubdate": run.startTime,
        }
    genRunexamples=exampleRunGen(runexamples.models.Run.objects.all())
    # merge both iterators
    return itertools.chain(genBuilds, genRunexamples)
  
  # reutrn feed entry title, description, link and pubdate
  def item_title(self, item):
    return item["title"]
  def item_description(self, item):
    return item["desc"]
  def item_link(self, item):
    return item["link"]
  def item_pubdate(self, item):
    return item["pubdate"]

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
