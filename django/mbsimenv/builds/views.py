import django
import django.shortcuts
import builds
import base.helper
import base.views
import functools
import service
import runexamples
import json
import re
import threading
import os
import datetime
import mbsimenvSecrets
import tempfile
from octicons.templatetags.octicons import octicon
from django.db.models import Q

# maps the current url to the proper run id url (without forwarding to keep the URL in the browser)
def currentBuildtypeBranch(request, buildtype, fmatvecBranch, hdf5serieBranch, openmbvBranch, mbsimBranch):
  run=builds.models.Run.objects.getCurrent(buildtype, fmatvecBranch, hdf5serieBranch, openmbvBranch, mbsimBranch)
  return Run.as_view()(request, id=run.id)

# the build page
class Run(base.views.Base):
  template_name='builds/run.html'
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    # the dataset of the build
    self.run=builds.models.Run.objects.get(id=self.kwargs["id"])

  def dispatch(self, request, *args, **kwargs):
    if "next" in self.request.GET:
      return django.shortcuts.redirect('builds:run', self.run.getNext().id)
    if "previous" in self.request.GET:
      return django.shortcuts.redirect('builds:run', self.run.getPrevious().id)
    if "current" in self.request.GET:
      return django.shortcuts.redirect('builds:current_buildtype_branch', self.run.buildType,
               self.run.fmatvecBranch, self.run.hdf5serieBranch, self.run.openmbvBranch, self.run.mbsimBranch)
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["buildsystem"]=True

    # get the corresponding examplerun ID to this build ID
    # and check if all these examples have passed or not
    examples=[]
    examplesAllOK=True
    for er in self.run.examples.all():
      ok=er.examples.filterFailed().count()==0
      examples.append({"id": er.id, "ok": ok, "buildType": er.buildType})
      if not ok: examplesAllOK=False

    context['run']=self.run
    context['runBuildTypeIcon']=base.helper.buildTypeIcon(self.run.buildType)
    # just a list which can be used to loop over in the template
    context['repos']=self.run.repos.values()
    for repo in context['repos']:
      repo["branchURLEvaluated"]=repo["branchURL"].format(branch=repo["branch"])
      repo["commitURLEvaluated"]=repo["commitURL"].format(sha=repo["updateCommitID"])
    context['examples']=examples
    context['examplesAllOK']=examplesAllOK
    context['releaseFileSuffix']="linux64.tar.bz2" if self.run.buildType=="linux64-dailyrelease" else "win64.zip"
    context['releaseTagSuffix']="linux64" if self.run.buildType=="linux64-dailyrelease" else "win64"
    context['releaseDistributionPossible']=base.helper.getExecutorID(self.run.executor)=="GITHUBACTION" or os.environ.get("MBSIMENVTAGNAME", "localhost")!="latest"

    allBranches=builds.models.Run.objects.filter(buildType=self.run.buildType).\
                  values("fmatvecBranch", "hdf5serieBranch", "openmbvBranch", "mbsimBranch").distinct()
    ab=[]
    for x in allBranches:
      if x["fmatvecBranch"]!="" and x["hdf5serieBranch"]!="" and x["openmbvBranch"]!="" and x["mbsimBranch"]!="":
        ab.append(x)
    context["allBranches"]=ab

    if self.run.fmatvecUpdateCommitID!="" and self.run.hdf5serieUpdateCommitID!="" and \
       self.run.openmbvUpdateCommitID!="" and self.run.mbsimUpdateCommitID!="":
      allBuildTypesPerSHA=list(builds.models.Run.objects.filter(fmatvecUpdateCommitID=self.run.fmatvecUpdateCommitID,
                                                                hdf5serieUpdateCommitID=self.run.hdf5serieUpdateCommitID,
                                                                openmbvUpdateCommitID=self.run.openmbvUpdateCommitID,
                                                                mbsimUpdateCommitID=self.run.mbsimUpdateCommitID).\
                                                                exclude(id=self.run.id).\
                                                                values("buildType", "id", "startTime").distinct())
      allBuildTypesPerSHAMap={}
      for cur in allBuildTypesPerSHA:
        curBuildType=cur["buildType"]
        curStartTime=cur["startTime"]
        if curBuildType not in allBuildTypesPerSHAMap:
          cur["icon"]=base.helper.buildTypeIcon(curBuildType)
          allBuildTypesPerSHAMap[curBuildType]=cur
        if curBuildType in allBuildTypesPerSHAMap and curStartTime>allBuildTypesPerSHAMap[curBuildType]["startTime"]:
          allBuildTypesPerSHAMap[curBuildType]["startTime"]=curStartTime
          allBuildTypesPerSHAMap[curBuildType]["id"]=cur["id"]
      allBuildTypesPerSHA=list(map(lambda x: allBuildTypesPerSHAMap[x], allBuildTypesPerSHAMap))
    else:
      allBuildTypesPerSHA=None
    if self.run.fmatvecBranch!="" and self.run.hdf5serieBranch!="" and self.run.openmbvBranch!="" and self.run.mbsimBranch!="":
      allBuildTypesPerBranch=list(builds.models.Run.objects.filter(fmatvecBranch=self.run.fmatvecBranch,
                                                                   hdf5serieBranch=self.run.hdf5serieBranch,
                                                                   openmbvBranch=self.run.openmbvBranch,
                                                                   mbsimBranch=self.run.mbsimBranch).\
                                                                   exclude(id=self.run.id).\
                                                                   values("buildType").distinct())
      for bt in allBuildTypesPerBranch:
        bt["icon"]=base.helper.buildTypeIcon(bt["buildType"])
    else:
      allBuildTypesPerBranch=None
    context["allBuildTypesPerSHA"]=allBuildTypesPerSHA
    context["allBuildTypesPerBranch"]=allBuildTypesPerBranch

    return context

# response to ajax requests of the build tool datatable
class DataTableTool(base.views.DataTable):
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.tools=builds.models.Tool.objects.filter(run=self.kwargs["run_id"])
  # return the queryset to display [required]
  @functools.lru_cache(maxsize=1)
  def queryset(self):
    return self.tools

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "toolName"

  def rowClass(self, ds):
    return "text-muted" if ds.willFail else ""

  # column visibility (all columns but be defined)
  def columnsVisibility(self):
    query=self.queryset().aggregate(
      configure=django.db.models.Count("configureOK"),
      make=django.db.models.Count("makeOK"),
      makeCheck=django.db.models.Count("makeCheckOK"),
      doc=django.db.models.Count("docOK"),
      xmldoc=django.db.models.Count("xmldocOK"),
    )
    vis={}
    vis["tool"]=True
    vis["configure"]=query["configure"]>0
    vis["make"]=query["make"]>0
    vis["makeCheck"]=query["makeCheck"]>0
    vis["doc"]=query["doc"]>0
    vis["xmldoc"]=query["xmldoc"]>0
    return vis

  # return the "data", "sort key" and "class" for columns ["data":required; "sort key" and "class":optional]

  def colData_tool(self, ds):
    return base.helper.tooltip(ds.toolName, "builds/Tool: id=%d"%(ds.id))
  def colSortKey_tool(self, ds):
    return ds.toolName
  def colClass_tool(self, ds):
    return "text-break"

  def colData_configure(self, ds):
    if ds.configureOK is None:
      return ""
    url=django.urls.reverse('base:textFieldFromDB', args=["builds", "Tool", ds.id, "configureOutput"])
    if ds.configureOK:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;<a href="%s">passed</a>'%(url)
    else:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)
  def colSortKey_configure(self, ds):
    return int(ds.configureOK) if ds.configureOK is not None else 2
  def colClass_configure(self, ds):
    if ds.configureOK is None:
      return ""
    return "table-success" if ds.configureOK else "table-danger"

  def colData_make(self, ds):
    if ds.makeOK is None:
      return ""
    url=django.urls.reverse('base:textFieldFromDB', args=["builds", "Tool", ds.id, "makeOutput"])
    if ds.makeOK:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;<a href="%s">passed</a>'%(url)
    else:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)
  def colSortKey_make(self, ds):
    return int(ds.makeOK) if ds.makeOK is not None else 2
  def colClass_make(self, ds):
    if ds.makeOK is None:
      return ""
    return "table-success" if ds.makeOK else "table-danger"

  def colData_makeCheck(self, ds):
    if ds.makeCheckOK is None:
      return ""
    url=django.urls.reverse('base:textFieldFromDB', args=["builds", "Tool", ds.id, "makeCheckOutput"])
    if ds.makeCheckOK:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;<a href="%s">passed</a>'%(url)
    else:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)
  def colSortKey_makeCheck(self, ds):
    return int(ds.makeCheckOK) if ds.makeCheckOK is not None else 2
  def colClass_makeCheck(self, ds):
    if ds.makeCheckOK is None:
      return ""
    return "table-success" if ds.makeCheckOK else "table-danger"

  def colData_doc(self, ds):
    if ds.docOK is None:
      return ""
    url=django.urls.reverse('base:textFieldFromDB', args=["builds", "Tool", ds.id, "docOutput"])
    if ds.docOK:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;<a href="%s">passed</a>'%(url)
    else:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)
  def colSortKey_doc(self, ds):
    return int(ds.docOK) if ds.docOK is not None else 2
  def colClass_doc(self, ds):
    if ds.docOK is None:
      return ""
    return "table-success" if ds.docOK else "table-danger"

  def colData_xmldoc(self, ds):
    if ds.xmldocOK is None:
      return ""
    url=django.urls.reverse('base:textFieldFromDB', args=["builds", "Tool", ds.id, "xmldocOutput"])
    if ds.xmldocOK:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;<a href="%s">passed</a>'%(url)
    else:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)
  def colSortKey_xmldoc(self, ds):
    return int(ds.xmldocOK) if ds.xmldocOK is not None else 2
  def colClass_xmldoc(self, ds):
    if ds.xmldocOK is None:
      return ""
    return "table-success" if ds.xmldocOK else "table-danger"

# release a distribution
def releaseDistribution(request, run_id):
  import github
  # prepare the cache for github access
  gh=base.helper.GithubCache(request)
  # if not logged in or not the appropriate right then return a http error
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout) and not base.helper.isLocalUser(request):
    return django.http.HttpResponseForbidden()
  # get data
  run=builds.models.Run.objects.get(id=run_id)
  releaseVersion=json.loads(request.body)["releaseVersion"]
  platform="win64" if run.buildType=="win64-dailyrelease" else "linux64"
  tagName="release/"+releaseVersion+"-"+platform
  relArchiveName="mbsim-env-release-"+releaseVersion+"-"+platform+(".zip" if run.buildType=="win64-dailyrelease" else ".tar.bz2")
  relArchiveDebugName="mbsim-env-release-"+releaseVersion+"-"+platform+"-debug"+(".zip" if run.buildType=="win64-dailyrelease" else ".tar.bz2")
  # check data
  if run.buildType!="win64-dailyrelease" and run.buildType!="linux64-dailyrelease":
    return django.http.HttpResponseBadRequest("Illegal build type for release.")
  if re.fullmatch("[0-9]+\.[0-9]+", releaseVersion) is None:
    return django.http.HttpResponseBadRequest("The version does not match x.y, where x and y are numbers.")
  if service.models.Release.objects.filter(versionMajor=releaseVersion.split(".")[0], versionMinor=releaseVersion.split(".")[1],
                                           platform=platform).count()>0:
    return django.http.HttpResponseBadRequest("A release for this platform with this version already exists.")
  if not run.distributionFile or not run.distributionDebugFile:
    return django.http.HttpResponseBadRequest("Release file (or debug file) not propably build.")

  if mbsimenvSecrets.getSecrets("githubAppSecret")!="":
    repos=['fmatvec', 'hdf5serie', 'openmbv', 'mbsim']
    # create tag object, create git reference and create a github release for all repositories
    # worker function to make github api requests in parallel
    def tagRefRelease(repo, out):
      try:
        if os.environ["MBSIMENVTAGNAME"]!="latest":
          print("Skipping setting rlease tags on github, this is the staging system!")
          out.clear()
          out['success']=True
          out['message']="Skipping setting rlease tags on github, this is the staging system!"
          return
        ghrepo=gh.getMbsimenvRepo(repo)
        commitid=getattr(run, repo+"UpdateCommitID")
        message="Release "+releaseVersion+" of MBSim-Env for "+platform+"\n"+\
                "\n"+\
                "The binary "+platform+" release can be downloaded from\n"+\
                "https://"+os.environ['MBSIMENVSERVERNAME']+django.urls.reverse("service:releases")+"\n"+\
                "Please note that this binary release includes a full build of MBSim-Env not only of this repository."
        # create github tag
        gittag=ghrepo.create_git_tag(tagName, message, commitid, "commit",
          tagger=github.InputGitAuthor(request.user.username, request.user.email,
                                       datetime.date.today().strftime("%Y-%m-%dT%H:%M:%SZ")))
        # create git tag
        ghrepo.create_git_ref("refs/tags/"+tagName, gittag.sha)
        # create release
        ghrepo.create_git_release(tagName, "Release "+releaseVersion+" of MBSim-Env for "+platform, message)
      except github.GithubException as ex:
        out.clear()
        out['success']=False
        out['message']=ex.data["message"] if "message" in ex.data else str(ex.data)
      except:
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
    error=False
    errorMsg=""
    for repo in repos:
      if not out[repo]['success']:
        error=True
      errorMsg=errorMsg+("\n" if len(out[repo]['message'])>0 else "")+out[repo]['message']
    if error:
      return django.http.HttpResponseBadRequest("Releasing failed:\n"+errorMsg)

  # create database release object
  r=service.models.Release()
  r.platform=platform
  r.createDate=datetime.date.today()
  r.versionMajor=releaseVersion.split(".")[0]
  r.versionMinor=releaseVersion.split(".")[1]
  r.releaseFileName=relArchiveName
  r.releaseDebugFileName=relArchiveDebugName
  r.save()

  # copying from django FileField to django FileField does not work for some reason
  try:
    tempF=tempfile.NamedTemporaryFile(mode='wb', delete=False)
    with run.distributionFile.open("rb") as fi:
      base.helper.copyFile(fi, tempF)
    tempF.close()
    with open(tempF.name, "rb") as fi:
      with r.releaseFile.open("wb") as fo:
        base.helper.copyFile(fi, fo)
  finally:
    os.unlink(tempF.name)

  try:
    tempF=tempfile.NamedTemporaryFile(mode='wb', delete=False)
    with run.distributionDebugFile.open("rb") as fi:
      base.helper.copyFile(fi, tempF)
    tempF.close()
    with open(tempF.name, "rb") as fi:
      with r.releaseDebugFile.open("wb") as fo:
        base.helper.copyFile(fi, fo)
  finally:
    os.unlink(tempF.name)

  return django.http.HttpResponse()

def runDistributionFileBuildtypeBranch(request, buildtype, fmatvecBranch, hdf5serieBranch, openmbvBranch, mbsimBranch):
  run=builds.models.Run.objects.getCurrent(buildtype, fmatvecBranch, hdf5serieBranch, openmbvBranch, mbsimBranch)
  return django.http.FileResponse(run.distributionFile, as_attachment=True, filename=run.distributionFileName)
def runDistributionDebugFileBuildtypeBranch(request, buildtype, fmatvecBranch, hdf5serieBranch, openmbvBranch, mbsimBranch):
  run=builds.models.Run.objects.getCurrent(buildtype, fmatvecBranch, hdf5serieBranch, openmbvBranch, mbsimBranch)
  return django.http.FileResponse(run.distributionDebugFile, as_attachment=True, filename=run.distributionDebugFileName)
def runDistributionFileID(request, id):
  run=builds.models.Run.objects.get(id=id)
  return django.http.FileResponse(run.distributionFile, as_attachment=True, filename=run.distributionFileName)
def runDistributionDebugFileID(request, id):
  run=builds.models.Run.objects.get(id=id)
  return django.http.FileResponse(run.distributionDebugFile, as_attachment=True, filename=run.distributionDebugFileName)

# create a new Run object which is unique wrt buildtype, executorID and git SHA IDs
# returns the integer runID of the new unique Run object or None as runID if no unique Run object could be created
# This is only useful for early checked of skipped builds without the need for the mbsimenv/build docker image
def createUniqueRunID(request, buildtype, executorID, fmatvecSHA, hdf5serieSHA, openmbvSHA, mbsimSHA,
                      fmatvecTriggered, hdf5serieTriggered, openmbvTriggered, mbsimTriggered):
  # check access token
  try: # catch all exceptions to avoid printing of any secrets
    if request.headers.get("Authorization", "")!="token "+mbsimenvSecrets.getSecrets("mbsimenvAccessToken"):
      return django.http.HttpResponseForbidden()
  except:
    return django.http.HttpResponseForbidden()

  run=builds.models.Run()
  run.buildType=buildtype
  run.executor='<span class="MBSIMENV_EXECUTOR_'+executorID+'"></span>' # dummy value (except the "executorID") is updated later
  run.startTime=django.utils.timezone.now() # dummy start time is updated later
  run.fmatvecUpdateCommitID=fmatvecSHA
  run.hdf5serieUpdateCommitID=hdf5serieSHA
  run.openmbvUpdateCommitID=openmbvSHA
  run.mbsimUpdateCommitID=mbsimSHA
  run.fmatvecTriggered=bool(fmatvecTriggered)
  run.hdf5serieTriggered=bool(hdf5serieTriggered)
  run.openmbvTriggered=bool(openmbvTriggered)
  run.mbsimTriggered=bool(mbsimTriggered)
  run.save()
  with django.db.transaction.atomic():
    reasentlyStarted=django.utils.timezone.now()-django.utils.timezone.timedelta(hours=12)
    existingRuns=builds.models.Run.objects.filter(
              Q(endTime__isnull=False) | (Q(endTime__isnull=True) & Q(startTime__gt=reasentlyStarted)),
              buildType=buildtype,
              fmatvecUpdateCommitID=fmatvecSHA, hdf5serieUpdateCommitID=hdf5serieSHA,
              openmbvUpdateCommitID=openmbvSHA, mbsimUpdateCommitID=mbsimSHA).\
              select_for_update().exclude(id=run.id) # filter existingRuns
    existingRuns2=[]
    for existingRun in existingRuns: # further filter existingRuns (by executorID)
      if base.helper.getExecutorID(existingRun.executor)==executorID:
        existingRuns2.append(existingRun)
    existingRuns=existingRuns2

    # if the same build already exits skip this build (return runID=None), except when references need to be updated
    if len(existingRuns)>0 and runexamples.models.ExampleStatic.objects.filter(update=True).count()==0:
      for repo in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
        triggered=functools.reduce(lambda a, b: a|b, [getattr(run, repo+"Triggered")]+[getattr(x, repo+"Triggered") for x in existingRuns])
        for existingRun in existingRuns:
          setattr(existingRun, repo+"Triggered", triggered)
          existingRun.save()
          try:
            r = existingRun.repos.get(repoName=repo)
            r.triggered=triggered
            r.save()
          except builds.models.Repos.DoesNotExist:
            pass
      builds.models.Run.objects.bulk_update(existingRuns, fields=["fmatvecTriggered", "hdf5serieTriggered", "openmbvTriggered", "mbsimTriggered"])
      run.delete()
      return django.http.JsonResponse({"runID": None, "existingRunIDs": [x.id for x in existingRuns]}, json_dumps_params={"indent": 2})
    return django.http.JsonResponse({"runID": run.id}, json_dumps_params={"indent": 2})
