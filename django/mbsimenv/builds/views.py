import django
import django.shortcuts
import builds
import base.helper
import base.views
import functools
import service
import json
import re
import threading
import os
import datetime
from octicons.templatetags.octicons import octicon

# maps the current url to the proper run id url (without forwarding to keep the URL in the browser)
def currentBuildtype(request, buildtype):
  run=builds.models.Run.objects.getCurrent(buildtype)
  return Run.as_view()(request, id=run.id)
def currentBuildtypePostfix(request, buildtype, postfix):
  run=builds.models.Run.objects.getCurrent(buildtype)
  resm=django.urls.resolve(django.urls.reverse('builds:run', args=[run.id])+postfix+"/")
  return resm.func(request, *resm.args, **resm.kwargs)

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
      return django.shortcuts.redirect('builds:current_buildtype', self.run.buildType) # use the special current URL in browser
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
    # just a list which can be used to loop over in the template
    context['repoList']=["fmatvec", "hdf5serie", "openmbv", "mbsim"]
    context['examples']=examples
    context['examplesAllOK']=examplesAllOK
    context['releaseFileSuffix']="linux64.tar.bz2" if self.run.buildType=="linux64-dailyrelease" else "win64.zip"
    context['releaseTagSuffix']="linux64" if self.run.buildType=="linux64-dailyrelease" else "win64"
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
    vis={}
    vis["tool"]=True
    vis["configure"]=self.queryset().filter(configureOK__isnull=False).count()>0
    vis["make"]=self.queryset().filter(makeOK__isnull=False).count()>0
    vis["makeCheck"]=self.queryset().filter(makeCheckOK__isnull=False).count()>0
    vis["doc"]=self.queryset().filter(docOK__isnull=False).count()>0
    vis["xmldoc"]=self.queryset().filter(xmldocOK__isnull=False).count()>0
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
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout):
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

  org="mbsim-env"
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
  with r.releaseFile.open("wb") as fo:
    with run.distributionFile.open("rb") as fi:
      fo.write(fi.read())
  with r.releaseDebugFile.open("wb") as fo:
    with run.distributionDebugFile.open("rb") as fi:
      fo.write(fi.read())
  return django.http.HttpResponse()

def runDistributionFile(request, id):
  run=builds.models.Run.objects.get(id=id)
  return django.http.FileResponse(run.distributionFile, as_attachment=True, filename=run.distributionFileName)
def runDistributionDebugFile(request, id):
  run=builds.models.Run.objects.get(id=id)
  return django.http.FileResponse(run.distributionDebugFile, as_attachment=True, filename=run.distributionDebugFileName)
