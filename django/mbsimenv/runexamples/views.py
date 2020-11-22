import django
import django.shortcuts
import runexamples
import base.views
import functools
import json
import urllib
import math
import os
import datetime
from octicons.templatetags.octicons import octicon

# maps the current url to the proper run id url (without forwarding to keep the URL in the browser)
def currentBuildtype(request, buildtype):
  run=runexamples.models.Run.objects.getCurrent(buildtype)
  return Run.as_view()(request, id=run.id)

# the examples page
class Run(base.views.Base):
  template_name='runexamples/run.html'
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    # prepare the cache for github access
    self.gh=base.helper.GithubCache(request)
    # the dataset of the examplerun
    self.run=runexamples.models.Run.objects.get(id=self.kwargs["id"])

  def dispatch(self, request, *args, **kwargs):
    if "next" in self.request.GET:
      return django.shortcuts.redirect('runexamples:run', self.run.getNext().id)
    if "previous" in self.request.GET:
      return django.shortcuts.redirect('runexamples:run', self.run.getPrevious().id)
    if "current" in self.request.GET:
      return django.shortcuts.redirect('runexamples:current_buildtype', self.run.buildType) # use the special current URL in browser
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)

    # check if this examplerun is the current (last one)
    isCurrent=self.run.getCurrent().id==self.run.id

    context['run']=self.run
    context['repoList']=["fmatvec", "hdf5serie", "openmbv", "mbsim"]
    # the checkboxes for refernece update are enabled for the current runexample and when the logged in user has the rights to do so
    context["enableUpdate"]=isCurrent and self.gh.getUserInMbsimenvOrg(base.helper.GithubCache.viewTimeout) and \
                            self.run.buildType=="linux64-dailydebug"
    return context

# handle ajax request to set example reference updates
def refUpdate(request, exampleName):
  # prepare the cache for github access
  gh=base.helper.GithubCache(request)
  # if not logged in or not the appropriate right then return a http error
  if not gh.getUserInMbsimenvOrg(base.helper.GithubCache.changesTimeout):
    return django.http.HttpResponseForbidden()
  # get the request data as json
  req=json.loads(request.body)
  # find the example on the the reference should be updated or create it
  try:
    ex=runexamples.models.ExampleStatic.objects.get(exampleName=urllib.parse.unquote(exampleName))
  except runexamples.models.ExampleStatic.DoesNotExist:
    ex=runexamples.models.ExampleStatic()
    ex.exampleName=urllib.parse.unquote(exampleName)
  # set the new update flag according the json data
  ex.update=req["update"]
  # save the dataset and return
  ex.save()
  return django.http.HttpResponse()

# response to ajax requests of the examples datatable
class DataTableExample(base.views.DataTable):
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.run=runexamples.models.Run.objects.get(id=self.kwargs["run_id"])
    self.isCurrent=self.run.getCurrent().id==self.run.id
    self.allowedUser=self.gh.getUserInMbsimenvOrg(base.helper.GithubCache.viewTimeout)

  # return the queryset to display [required]
  @functools.lru_cache(maxsize=1)
  def queryset(self):
    return self.run.examples

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "exampleName"

  # column visibility (all columns but be defined)
  def columnsVisibility(self):
    query=self.queryset().aggregate(
      run=django.db.models.Count("runResult"),
      time=django.db.models.Count("time"),
      guiTestHdf5serie=django.db.models.Count("guiTestHdf5serieOK"),
      guiTestOpenmbv=django.db.models.Count("guiTestOpenmbvOK"),
      guiTestMbsimgui=django.db.models.Count("guiTestMbsimguiOK"),
      ref=django.db.models.Count("resultFiles"),
      webAppHdf5serie=django.db.models.Count(django.db.models.Case(django.db.models.When(
        webappHdf5serie=True, then=django.db.models.Value(1)))),
      webAppOpenmbv=django.db.models.Count(django.db.models.Case(django.db.models.When(
        webappOpenmbv=True, then=django.db.models.Value(1)))),
      webAppMbsimgui=django.db.models.Count(django.db.models.Case(django.db.models.When(
        webappMbsimgui=True, then=django.db.models.Value(1)))),
      dep=django.db.models.Count("deprecatedNr"),
      xmlOut=django.db.models.Count("xmlOutputs"),
    )

    vis={}
    vis["example"]=True
    vis["run"]=query["run"]>0
    vis["time"]=query["time"]>0
    vis["refTime"]=runexamples.models.ExampleStatic.objects.filter(
                   exampleName__in=self.queryset().values_list('exampleName', flat=True)).count()>0
    vis["guiTest"]=query["guiTestHdf5serie"]+query["guiTestOpenmbv"]+query["guiTestMbsimgui"]>0
    vis["ref"]=query["ref"]>0
    vis["webApp"]=query["webAppHdf5serie"]+query["webAppOpenmbv"]+query["webAppMbsimgui"]>0
    vis["dep"]=query["dep"]>0
    vis["xmlOut"]=query["xmlOut"]>0
    return vis

  # return the field name in the dataset using for search/filter [optional]
  def rowClass(self, ds):
    return "text-muted" if ds.willFail else ""

  # get the static example dataset corresponding to this dataset
  def getStaticDS(self, ds):
    try:
      return runexamples.models.ExampleStatic.objects.get(exampleName=ds.exampleName)
    except runexamples.models.ExampleStatic.DoesNotExist:
      return None

  # get the reference time of the static dataset
  def getRefTime(self, ds):
    dsStatic=self.getStaticDS(ds)
    if dsStatic is None:
      return None
    return dsStatic.refTime

  # return the "data", "sort key" and "class" for columns ["data":required; "sort key" and "class":optional]

  def colData_example(self, ds):
    return base.helper.tooltip(ds.exampleName, "runexamples/Example: id=%d"%(ds.id))
  def colSortKey_example(self, ds):
    return ds.exampleName
  def colClass_example(self, ds):
    return "text-break"

  def colData_run(self, ds):
    if ds.runResult==runexamples.models.Example.RunResult.PASSED:
      icon='<span class="text-success">'+octicon("check")+'</span>'
      text="passed"
    elif ds.runResult==runexamples.models.Example.RunResult.TIMEDOUT:
      icon='<span class="text-danger">'+octicon("stop")+'</span>'
      text="timed out"
    elif ds.runResult==runexamples.models.Example.RunResult.FAILED:
      icon='<span class="text-danger">'+octicon("stop")+'</span>'
      text="failed"
    else:
      icon=""
      text=""
    url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "Example", ds.id, "runOutput"])
    ret='%s&nbsp;<a href="%s">%s</a>'%(icon, url, text)
    # valgrind
    if ds.valgrinds.filter(programType__startswith="example_").count()>0:
      ret+='''<div class="dropdown">
                <button class="btn btn-secondary btn-xs" type="button" data-toggle="dropdown">valgrind {}</button>
                <div class="dropdown-menu">'''.format(octicon("triangle-down"))
      for vg in ds.valgrinds.filter(programType__startswith="example_"):
        valgrindNrErrors=runexamples.models.Valgrind.objects.get(id=vg.id).errors.all().count()
        ret+='<a class="dropdown-item text-{}" href="{}">{}{}</a>'.\
          format("success" if valgrindNrErrors==0 else "danger",
                 django.urls.reverse('runexamples:valgrind', args=[vg.id]),
                 vg.programType[len("example_"):],
                 '&nbsp;<span class="badge badge-danger">%d</span>&nbsp;errors'%(valgrindNrErrors) if valgrindNrErrors>0 else "")
      ret+='</div></div>'
    return ret
  def colSortKey_run(self, ds):
    if ds.willFail: return 2
    if ds.runResult is None: return 1
    return int(-ds.runResult)
  def colClass_run(self, ds):
    return "table-success" if ds.runResult==runexamples.models.Example.RunResult.PASSED and not ds.willFail or \
                              ds.runResult!=runexamples.models.Example.RunResult.PASSED and ds.willFail else "table-danger"

  def colData_time(self, ds):
    return str(datetime.timedelta(seconds=round(ds.time.total_seconds()))) if ds.time is not None else ""
  def colSortKey_time(self, ds):
    return ds.time.total_seconds() if ds.time is not None else 1.0e50
  def colClass_time(self, ds):
    if self.getRefTime(ds) is None or ds.time is None or ds.time <= self.getRefTime(ds)*1.1:
      return "table-success"
    else:
      return "table-warning"

  def colData_refTime(self, ds):
    return str(datetime.timedelta(seconds=round(self.getRefTime(ds).total_seconds()))) if self.getRefTime(ds) is not None else ""
  def colSortKey_refTime(self, ds):
    return self.getRefTime(ds).total_seconds() if self.getRefTime(ds) is not None else 1.0e50

  def colData_guiTest(self, ds):
    ret=""
    url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "Example", ds.id, "guiTestOpenmbvOutput"])
    vis="visible" if ds.guiTestOpenmbvOK is not None else "hidden"
    ok="success" if ds.guiTestOpenmbvOK==runexamples.models.Example.GUITestResult.PASSED else ("warning" if ds.guiTestOpenmbvOK==runexamples.models.Example.GUITestResult.TIMEDOUT or ds.willFail else "danger")
    img=django.templatetags.static.static("base/openmbv.svg")
    ret+='<a href="%s"><button type="button" style="visibility:%s;" class="btn btn-%s btn-xs">'%(url, vis, ok)+\
           '<img src="%s" alt="ombv"/></button></a>&nbsp;'%(img)
    url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "Example", ds.id, "guiTestHdf5serieOutput"])
    vis="visible" if ds.guiTestHdf5serieOK is not None else "hidden"
    ok="success" if ds.guiTestHdf5serieOK==runexamples.models.Example.GUITestResult.PASSED else ("warning" if ds.guiTestHdf5serieOK==runexamples.models.Example.GUITestResult.TIMEDOUT or ds.willFail else "danger")
    img=django.templatetags.static.static("base/h5plotserie.svg")
    ret+='<a href="%s"><button type="button" style="visibility:%s;" class="btn btn-%s btn-xs">'%(url, vis, ok)+\
           '<img src="%s" alt="h5p"/></button></a>&nbsp;'%(img)
    url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "Example", ds.id, "guiTestMbsimguiOutput"])
    vis="visible" if ds.guiTestMbsimguiOK is not None else "hidden"
    ok="success" if ds.guiTestMbsimguiOK==runexamples.models.Example.GUITestResult.PASSED else ("warning" if ds.guiTestMbsimguiOK==runexamples.models.Example.GUITestResult.TIMEDOUT or ds.willFail else "danger")
    img=django.templatetags.static.static("base/mbsimgui.svg")
    ret+='<a href="%s"><button type="button" style="visibility:%s;" class="btn btn-%s btn-xs">'%(url, vis, ok)+\
           '<img src="%s" alt="gui"/></button></a>'%(img)
    # valgrind
    if ds.valgrinds.filter(programType__startswith="guitest_").count()>0:
      ret+='''<div class="dropdown">
                <button class="btn btn-secondary btn-xs" type="button" data-toggle="dropdown">valgrind {}</button>
                <div class="dropdown-menu">'''.format(octicon("triangle-down"))
      for vg in ds.valgrinds.filter(programType__startswith="guitest_"):
        valgrindNrErrors=runexamples.models.Valgrind.objects.get(id=vg.id).errors.all().count()
        ret+='<a class="dropdown-item text-{}" href="{}">{}{}</a>'.\
          format("success" if valgrindNrErrors==0 else "danger",
                 django.urls.reverse('runexamples:valgrind', args=[vg.id]),
                 vg.programType[len("guitest_"):],
                 '&nbsp;<span class="badge badge-danger">%d</span>&nbsp;errors'%(valgrindNrErrors) if valgrindNrErrors>0 else "")
      ret+='</div></div>'
    return ret
  def colSortKey_guiTest(self, ds):
    m={None:                                            0,
       runexamples.models.Example.RunResult.PASSED:     1,
       runexamples.models.Example.RunResult.FAILED:    10,
       runexamples.models.Example.RunResult.TIMEDOUT: 100}
    return -(m[ds.guiTestOpenmbvOK]+m[ds.guiTestHdf5serieOK]+m[ds.guiTestMbsimguiOK])

  def colData_ref(self, ds):
    refUrl=django.urls.reverse('runexamples:compareresult', args=[ds.id])
    updateUrl=django.urls.reverse('runexamples:ref_update', args=[urllib.parse.quote(ds.exampleName, safe="")])
    dsStatic=self.getStaticDS(ds)
    checked='checked="checked"' if dsStatic is not None and dsStatic.update else ""
    refCheckbox='<span class="float-right">[<input type="checkbox" onClick="changeRefUpdate($(this), \'%s\', \'%s\');" %s/>]</span>'%\
                (updateUrl, ds.exampleName, checked) \
                if self.isCurrent and self.allowedUser and self.run.buildType=="linux64-dailydebug" else ""
    if ds.resultFiles.count()==0:
      ret='<span class="float-left"><span class="text-warning">%s</span>&nbsp;no reference</span>%s'%\
          (octicon("alert"), refCheckbox)
    elif ds.resultsFailed==0:
      ret='<span class="float-left"><span class="text-success">%s</span>&nbsp;<a href="%s">passed '\
          '</a></span>'%(octicon("check"), refUrl)
    else:
      ret='<span class="float-left"><span class="text-danger">%s</span>&nbsp;<a href="%s">failed '\
          '<span class="badge badge-secondary">%d</span></a></span>%s'%\
          (octicon("stop"), refUrl, ds.resultsFailed, refCheckbox)
    return ret
  def colClass_ref(self, ds):
    if ds.resultFiles.count()==0:
      return 'table-warning'
    elif ds.resultsFailed==0:
      return 'table-success'
    else:
      return 'table-danger'
  def colSortKey_ref(self, ds):
    if ds.resultFiles.count()==0:
      return -0
    elif ds.resultsFailed==0:
      return -1
    else:
      return -2

  def colData_webApp(self, ds):
    ret=""
    addLink=True if self.isCurrent and self.allowedUser else False
    enabled="" if addLink else 'disabled="disabled"'
    notLoggedInTooltipAttr=' data-toggle="tooltip" data-placement="bottom" title="You need to be logged in to start the web app!"' \
                           if not addLink else ""

    url=django.urls.reverse('service:webapp', args=["openmbv", self.run.buildType, ds.exampleName])
    vis="visible" if ds.webappOpenmbv else "hidden"
    img=django.templatetags.static.static("base/openmbv.svg")
    ret+=('<a href="%s">'%(url) if addLink else "") +\
         '<button %s type="button" class="btn btn-outline-primary btn-xs" style="visibility:%s;"%s>'\
         '<img src="%s" alt="ombv"/></button>'%(enabled, vis, notLoggedInTooltipAttr, img)+('</a>' if addLink else "")+'&nbsp;'

    url=django.urls.reverse('service:webapp', args=["h5plotserie", self.run.buildType, ds.exampleName])
    vis="visible" if ds.webappHdf5serie else "hidden"
    img=django.templatetags.static.static("base/h5plotserie.svg")
    ret+=('<a href="%s">'%(url) if addLink else "")+\
         '<button %s type="button" class="btn btn-outline-primary btn-xs" style="visibility:%s;"%s>'\
         '<img src="%s" alt="h5p"/></button>'%(enabled, vis, notLoggedInTooltipAttr, img)+('</a>' if addLink else "")+'&nbsp;'

    url=django.urls.reverse('service:webapp', args=["mbsimgui", self.run.buildType, ds.exampleName])
    vis="visible" if ds.webappMbsimgui else "hidden"
    img=django.templatetags.static.static("base/mbsimgui.svg")
    ret+=('<a href="%s">'%(url) if addLink else "")+\
         '<button %s type="button" class="btn btn-outline-primary btn-xs" style="visibility:%s;"%s>'\
         '<img src="%s" alt="gui"/></button>'%(enabled, vis, notLoggedInTooltipAttr, img)+('</a>' if addLink else "")

    return ret
  def colSortKey_webApp(self, ds):
    return -(ds.webappOpenmbv+ds.webappHdf5serie+ds.webappMbsimgui)

  def colData_dep(self, ds):
    if ds.deprecatedNr is not None and ds.deprecatedNr>0:
      url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "Example", ds.id, "runOutput"])
      return octicon("alert")+'&nbsp;<a href="%s"><span class="badge badge-secondary">%d</span> found</a></td>'%\
        (url, ds.deprecatedNr)
    else:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;none'
  def colClass_dep(self, ds):
    if ds.deprecatedNr is not None and ds.deprecatedNr>0:
      return 'table-warning'
    else:
      return 'table-success'
  def colSortKey_dep(self, ds):
    return -ds.deprecatedNr if ds.deprecatedNr is not None else 0

  def colData_xmlOut(self, ds):
    nrAll=ds.xmlOutputs.count()
    if nrAll==0:
      return ""
    nrFailed=ds.xmlOutputs.filterFailed().count()
    if nrFailed==0:
      icon='<span class="text-success">'+octicon("check")+'</span>'
      text="valid"
      nr=nrAll
    else:
      icon='<span class="text-danger">'+octicon("stop")+'</span>'
      text="failed"
      nr=nrFailed
    url=django.urls.reverse('runexamples:xmloutput', args=[ds.id])
    return '%s&nbsp;<a href="%s">%s<span class="badge badge-secondary">%d</span></a>'%(icon, url, text, nr)
  def colClass_xmlOut(self, ds):
    if ds.xmlOutputs.count()==0:
      return ""
    if ds.xmlOutputs.filterFailed().count()==0:
      return 'table-success'
    else:
      return 'table-danger'
  def colSortKey_xmlOut(self, ds):
    return ds.xmlOutputs.filterFailed().count()==0

class Valgrind(base.views.Base):
  template_name='runexamples/valgrind.html'
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.valgrind=runexamples.models.Valgrind.objects.get(id=self.kwargs["id"])
  def dispatch(self, request, *args, **kwargs):
    if "next" in self.request.GET:
      return django.shortcuts.redirect('runexamples:valgrind', self.example.getNext().id)
    if "previous" in self.request.GET:
      return django.shortcuts.redirect('runexamples:valgrind', self.example.getPrevious().id)
    if "current" in self.request.GET:
      return django.shortcuts.redirect('runexamples:valgrind', self.example.getCurrent().id)
    return super().dispatch(request, *args, **kwargs)
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["valgrind"]=self.valgrind
    return context

class DataTableValgrindError(base.views.DataTable):
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.errors=runexamples.models.Valgrind.objects.get(id=self.kwargs["id"]).errors

  # return the queryset to display [required]
  def queryset(self):
    return self.errors

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "kind"

  def isLeak(self, ds):
    return ds.kind.startswith("Leak_")

  @staticmethod
  def vertText(text, bold=False, size=16):
    return '''<svg width="%d" height="%d">
      <text style="font-weight:%s;font-size:%dpx;font-family:sans-serif;text-anchor:middle;" x="-%d" y="%d" transform="rotate(-90)">%s</text>
    </svg>'''%(size, size*len(text), "bold" if bold else "normal", size, round(size*len(text)/2), round(0.8*size), text)

  # return the "data", "sort key" and "class" for columns ["data":required; "sort key" and "class":optional]

  def colData_kind(self, ds):
    return base.helper.tooltip(
   '''<span class="dropdown">
        <button class="btn btn-secondary btn-xs" type="button" data-toggle="dropdown">
          supp&nbsp;{}
        </button>
        <pre class="dropdown-menu" style="padding-left: 0.5em; padding-right: 0.5em;">{}</pre>
      </span><br/>'''.format(octicon("triangle-down"), ds.suppressionRawText)+\
      self.vertText(ds.kind, True, 24), "runexamples/ValgrindError: id=%s"%(ds.id))
  def colSort_kind(self, ds):
    return ("1" if self.isLeak(ds) else "0")+"_"+ds.kind
  def colClass_kind(self, ds):
    return 'table-warning' if self.isLeak(ds) else "table-danger"

  def colData_detail(self, ds):
    ret=""
    for ws in ds.whatsAndStacks.order_by("nr"):
      ret+='<h5 class="text-danger">'+ws.what+'</h5>'
      ret+='''
        <table id="{}" data-url="{}" class="table table-striped table-hover table-bordered table-sm w-100">
          <thead>
            <tr>
              <th>File:Line</th>
              <th>Function Name</th>
              <th>Library</th>
            </tr>
          </thead>
          <tbody>
          </tbody>
        </table>'''.format("valgrindStackTable_"+str(ws.id),
                           django.urls.reverse('runexamples:datatable_valgrindstack', args=[ws.id]))
    return ret
  def colSort_detail(self, ds):
    return ""

class DataTableValgrindStack(base.views.DataTable):
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.stacks=runexamples.models.ValgrindWhatAndStack.objects.get(id=self.kwargs["id"]).stacks

  def defaultOrderingColName(self):
    return "nr"

  # return the queryset to display [required]
  def queryset(self):
    return self.stacks

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "file" # just a dummy

  # return the "data", "sort key" and "class" for columns ["data":required; "sort key" and "class":optional]

  def colData_fileLine(self, ds):
    path=""
    if ds.dir!="": path+=ds.dir+"/"
    if ds.file!="": path+=ds.file
    text=(path+":"+str(ds.line)) if ds.line is not None else path
    if text=="": text="-"
    repo=next(filter(lambda r: path.startswith("/mbsim-env/%s/"%(r)), ["fmatvec", "hdf5serie", "openmbv", "mbsim"]), None)
    if repo is not None:
      buildRun=ds.whatAndStack.valgrindError.valgrind.example.run.build_run
      if buildRun is None:
        return base.helper.tooltip(text, "runexamples/ValgrindWhatAndStack: id=%d"%(ds.id))
      commitID=getattr(buildRun, repo+"UpdateCommitID")
      return base.helper.tooltip('<a href="https://github.com/mbsim-env/%s/blob/%s/%s#L%d">%s</a>'%\
        (repo, commitID, path[len("/mbsim-env/"+repo+"/"):], ds.line if ds.line is not None else 0, text),
        "runexamples/ValgrindWhatAndStack: id=%d"%(ds.id))
    else:
      return base.helper.tooltip(text, "runexamples/ValgrindWhatAndStack: id=%d"%(ds.id))
  def colClass_fileLine(self, ds):
    return "text-break"

  def colData_function(self, ds):
    return ds.fn
  def colClass_function(self, ds):
    return "text-break"

  def colData_library(self, ds):
    return ds.obj
  def colClass_library(self, ds):
    return "text-break"

# xml output page
class XMLOutput(base.views.Base):
  template_name='runexamples/xmloutput.html'
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.example=runexamples.models.Example.objects.get(id=self.kwargs["id"])

  def dispatch(self, request, *args, **kwargs):
    if "next" in self.request.GET:
      return django.shortcuts.redirect('runexamples:xmloutput', self.example.getNext().id)
    if "previous" in self.request.GET:
      return django.shortcuts.redirect('runexamples:xmloutput', self.example.getPrevious().id)
    if "current" in self.request.GET:
      return django.shortcuts.redirect('runexamples:xmloutput', self.example.getCurrent().id)
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context['example']=self.example
    return context

class DataTableXMLOutput(base.views.DataTable):
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.xmlOutputs=runexamples.models.Example.objects.get(id=self.kwargs["id"]).xmlOutputs

  # return the queryset to display [required]
  def queryset(self):
    return self.xmlOutputs

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "filename"

  # return the "data", "sort key" and "class" for columns ["data":required; "sort key" and "class":optional]

  def colData_file(self, ds):
    return base.helper.tooltip(ds.filename, "runexamples/XMLOutput: id=%d"%(ds.id))
  def colSortKey_file(self, ds):
    return ds.filename
  def colClass_file(self, ds):
    return "text-break"

  def colData_result(self, ds):
    url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "XMLOutput", ds.id, "resultOutput"])
    if ds.resultOK:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;<a href="%s">passed</a>'%(url)
    else:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)
  def colSortKey_result(self, ds):
    return ds.resultOK
  def colClass_result(self, ds):
    if ds.resultOK:
      return "table-success"
    else:
      return "table-danger"

# compare result output page
class CompareResult(base.views.Base):
  template_name='runexamples/compareresult.html'
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.example=runexamples.models.Example.objects.get(id=self.kwargs["id"])

  def dispatch(self, request, *args, **kwargs):
    if "next" in self.request.GET:
      return django.shortcuts.redirect('runexamples:compareresult', self.example.getNext().id)
    if "previous" in self.request.GET:
      return django.shortcuts.redirect('runexamples:compareresult', self.example.getPrevious().id)
    if "current" in self.request.GET:
      return django.shortcuts.redirect('runexamples:compareresult', self.example.getCurrent().id)
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context['example']=self.example
    return context

class DataTableCompareResult(base.views.DataTable):
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.allResults=runexamples.models.CompareResult.objects.filter(compareResultFile__example__id=self.kwargs["id"])

  # return the queryset to display [required]
  def queryset(self):
    return self.allResults

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "compareResultFile__h5Filename"

  # return the "data", "sort key" and "class" for columns ["data":required; "sort key" and "class":optional]

  def colData_h5file(self, ds):
    return base.helper.tooltip(ds.compareResultFile.h5Filename, "runexamples/CompareResult: id=%d"%(ds.id))
  def colSortKey_h5file(self, ds):
    return ds.compareResultFile.h5Filename if ds.compareResultFile.h5Filename is not None else ""
  def colClass_h5file(self, ds):
    return "text-break"

  def colData_dataset(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[file not in cur]'
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINREF:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[file not in ref]'
    return ds.dataset
  def colClass_dataset(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR or ds.result==runexamples.models.CompareResult.Result.FILENOTINREF:
      return 'table-danger text-break'
    return 'text-break'

  def colData_label(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR or ds.result==runexamples.models.CompareResult.Result.FILENOTINREF:
      return ''
    if ds.result==runexamples.models.CompareResult.Result.DATASETNOTINCUR:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[dataset not in cur]'
    if ds.result==runexamples.models.CompareResult.Result.DATASETNOTINREF:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[dataset not in ref]'
    return ds.label
  def colClass_label(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR or ds.result==runexamples.models.CompareResult.Result.FILENOTINREF:
      return 'text-break'
    if ds.result==runexamples.models.CompareResult.Result.DATASETNOTINCUR or ds.result==runexamples.models.CompareResult.Result.DATASETNOTINREF:
      return 'table-danger text-break'
    return 'text-break'

  def colData_result(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR or ds.result==runexamples.models.CompareResult.Result.FILENOTINREF or \
       ds.result==runexamples.models.CompareResult.Result.DATASETNOTINCUR or ds.result==runexamples.models.CompareResult.Result.DATASETNOTINREF:
      return ''
    if ds.result==runexamples.models.CompareResult.Result.LABELNOTINCUR:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[label not in cur]'
    if ds.result==runexamples.models.CompareResult.Result.LABELNOTINREF:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[label not in ref]'
    if ds.result==runexamples.models.CompareResult.Result.LABELDIFFER:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[label differ]'
    if ds.result==runexamples.models.CompareResult.Result.LABELMISSING:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[label missing]'
    if ds.result==runexamples.models.CompareResult.Result.PASSED:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;passed'
    url=django.urls.reverse('runexamples:differenceplot', args=[ds.id])
    return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)
  def colSortKey_result(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FAILED:
      return -9
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR:
      return -8
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINREF:
      return -7
    if ds.result==runexamples.models.CompareResult.Result.DATASETNOTINCUR:
      return -6
    if ds.result==runexamples.models.CompareResult.Result.DATASETNOTINREF:
      return -5
    if ds.result==runexamples.models.CompareResult.Result.LABELNOTINCUR:
      return -4
    if ds.result==runexamples.models.CompareResult.Result.LABELNOTINREF:
      return -3
    if ds.result==runexamples.models.CompareResult.Result.LABELDIFFER:
      return -2
    if ds.result==runexamples.models.CompareResult.Result.LABELMISSING:
      return -1
    if ds.result==runexamples.models.CompareResult.Result.PASSED:
      return -0
    return 1
  def colClass_result(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR or ds.result==runexamples.models.CompareResult.Result.FILENOTINREF or \
       ds.result==runexamples.models.CompareResult.Result.DATASETNOTINCUR or ds.result==runexamples.models.CompareResult.Result.DATASETNOTINREF:
      return ''
    if ds.result==runexamples.models.CompareResult.Result.LABELNOTINCUR or ds.result==runexamples.models.CompareResult.Result.LABELNOTINREF or \
       ds.result==runexamples.models.CompareResult.Result.LABELDIFFER or ds.result==runexamples.models.CompareResult.Result.LABELMISSING:
      return 'table-danger'
    if ds.result==runexamples.models.CompareResult.Result.PASSED:
      return 'table-success'
    return 'table-danger'

# difference plot output page
class DifferencePlot(base.views.Base):
  template_name='runexamples/differenceplot.html'
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    self.compareResult=runexamples.models.CompareResult.objects.get(id=self.kwargs["id"])

  def dispatch(self, request, *args, **kwargs):
    if "next" in self.request.GET:
      return django.shortcuts.redirect('runexamples:differenceplot', self.compareResult.getNext().id)
    if "previous" in self.request.GET:
      return django.shortcuts.redirect('runexamples:differenceplot', self.compareResult.getPrevious().id)
    if "current" in self.request.GET:
      return django.shortcuts.redirect('runexamples:differenceplot', self.compareResult.getCurrent().id)
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context['compareResult']=self.compareResult
    return context

# response to ajax requests -> output repository branches
def chartDifferencePlot(request, id):
  import h5py
  import tempfile
  import numpy

  # get current result
  compareResult=runexamples.models.CompareResult.objects.get(id=id)
  with compareResult.compareResultFile.h5File.open("rb") as djangoF:
    try:
      tempF=tempfile.NamedTemporaryFile(mode='wb', delete=False)
      tempF.write(djangoF.read())
      tempF.close()
      h5F=h5py.File(tempF.name, "r")
      dataset=h5F[compareResult.dataset]
      colIdx=dataset.attrs["Column Label"].tolist().index(compareResult.label.encode("utf-8"))
      timeCur=dataset[:,0].reshape((dataset.shape[0],1))
      cur=dataset[:,colIdx]
    finally:
      os.unlink(tempF.name)

  def np2Json(np):
    return list(map(lambda x: [x[0],0] if math.isnan(x[1]) else x, np.tolist()))
  # get reference result
  try:
    exampleStatic=runexamples.models.ExampleStatic.objects.get(exampleName=compareResult.compareResultFile.example.exampleName)
    for r in exampleStatic.references.all():
      if r.h5FileName==compareResult.compareResultFile.h5FileName:
        break
    with r.h5File.open("rb") as djangoF:
      try:
        tempF=tempfile.NamedTemporaryFile(mode='wb', delete=False)
        tempF.write(djangoF.read())
        tempF.close()
        h5F=h5py.File(tempF.name, "r")
        dataset=h5F[compareResult.dataset]
        colIdx=dataset.attrs["Column Label"].tolist().index(compareResult.label.encode("utf-8"))
        timeRef=dataset[:,0].reshape((dataset.shape[0],1))
        ref=dataset[:,colIdx]
      finally:
        os.unlink(tempF.name)

    if ref.shape==cur.shape and numpy.all(numpy.isclose(timeCur, timeRef, rtol=1e-12, atol=1e-12, equal_nan=True)):
      absErr=abs(ref-cur)
      relErr=absErr/(abs(ref)+1.0e-14) # avoid diff my zero
    else:
      absErr=None
      relErr=None
    return django.http.JsonResponse({
      "reference": np2Json(numpy.concatenate((timeRef,ref.reshape((dataset.shape[0],1))), axis=1)),
      "current": np2Json(numpy.concatenate((timeCur,cur.reshape((timeCur.shape[0],1))), axis=1)),
      "abs": None if absErr is None else np2Json(numpy.concatenate((timeCur,absErr.reshape((dataset.shape[0],1))), axis=1)),
      "rel": None if relErr is None else np2Json(numpy.concatenate((timeCur,relErr.reshape((dataset.shape[0],1))), axis=1)),
    })
  except:
    return django.http.JsonResponse({
      "reference": None,
      "current": np2Json(numpy.concatenate((timeCur,cur.reshape((timeCur.shape[0],1))), axis=1)),
      "abs": None,
      "rel": None,
    })

def allExampleStatic(request):
  allEx={}
  for ex in runexamples.models.ExampleStatic.objects.all():
    references=[]
    for ref in ex.references.all():
      references.append({"id": ref.id, "h5FileName": ref.h5FileName, "h5FileSHA1": ref.h5FileSHA1})
    allEx[ex.exampleName]={
      "refTime": ex.refTime.total_seconds(),
      "references": references,
    }
  return django.http.JsonResponse(allEx)
