import django
import django.shortcuts
import runexamples
import base.views
import functools
import json
import urllib
import math
import os
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
    context["enableUpdate"]=isCurrent and self.gh.getUserInMbsimenvOrg(base.helper.GithubCache.viewTimeout)
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
      ref=django.db.models.Count("results"),
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
    vis["ref"]=query["ref"]
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
    return ds.exampleName.replace("/", "/\u200b")
  def colSortKey_example(self, ds):
    return ds.exampleName

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
        ret+='<a class="dropdown-item" href="{}">{}</a>'.\
          format(django.urls.reverse('runexamples:valgrind', args=[vg.id]), vg.programType[len("example_"):])
      ret+='</div></div>'
    return ret
  def colSortKey_run(self, ds):
    return ds.runResult
  def colClass_run(self, ds):
    return "table-success" if ds.runResult==runexamples.models.Example.RunResult.PASSED and not ds.willFail or \
                              ds.runResult!=runexamples.models.Example.RunResult.PASSED and ds.willFail else "table-danger"

  def colData_time(self, ds):
    return str(ds.time) if ds.time is not None else ""
  def colClass_time(self, ds):
    if self.getRefTime(ds) is None or ds.time is None or ds.time <= self.getRefTime(ds)*1.1:
      return "table-success"
    else:
      return "table-warning"

  def colData_refTime(self, ds):
    return str(self.getRefTime(ds)) if self.getRefTime(ds) is not None else ""

  def colData_guiTest(self, ds):
    ret=""
    url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "Example", ds.id, "guiTestOpenmbvOutput"])
    vis="visible" if ds.guiTestOpenmbvOK is not None else "hidden"
    ok="success" if ds.guiTestOpenmbvOK else ("warning" if ds.willFail else "danger")
    img=django.templatetags.static.static("base/openmbv.svg")
    ret+='<a href="%s"><button type="button" style="visibility:%s;" class="btn btn-%s btn-xs">'%(url, vis, ok)+\
           '<img src="%s" alt="ombv"/></button></a>&nbsp;'%(img)
    url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "Example", ds.id, "guiTestHdf5serieOutput"])
    vis="visible" if ds.guiTestHdf5serieOK is not None else "hidden"
    ok="success" if ds.guiTestHdf5serieOK else ("warning" if ds.willFail else "danger")
    img=django.templatetags.static.static("base/h5plotserie.svg")
    ret+='<a href="%s"><button type="button" style="visibility:%s;" class="btn btn-%s btn-xs">'%(url, vis, ok)+\
           '<img src="%s" alt="h5p"/></button></a>&nbsp;'%(img)
    url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "Example", ds.id, "guiTestMbsimguiOutput"])
    vis="visible" if ds.guiTestMbsimguiOK is not None else "hidden"
    ok="success" if ds.guiTestMbsimguiOK else ("warning" if ds.willFail else "danger")
    img=django.templatetags.static.static("base/mbsimgui.svg")
    ret+='<a href="%s"><button type="button" style="visibility:%s;" class="btn btn-%s btn-xs">'%(url, vis, ok)+\
           '<img src="%s" alt="gui"/></button></a>'%(img)
    # valgrind
    if ds.valgrinds.filter(programType__startswith="guitest_").count()>0:
      ret+='''<div class="dropdown">
                <button class="btn btn-secondary btn-xs" type="button" data-toggle="dropdown">valgrind {}</button>
                <div class="dropdown-menu">'''.format(octicon("triangle-down"))
      for vg in ds.valgrinds.filter(programType__startswith="guitest_"):
        ret+='<a class="dropdown-item" href="{}">{}</a>'.\
          format(django.urls.reverse('runexamples:valgrind', args=[vg.id]), vg.programType[len("guitest_"):])
      ret+='</div></div>'
    return ret
  def colSortKey_guiTest(self, ds):
    ret=""
    ret+="0" if ds.guiTestOpenmbvOK   is None or ds.guiTestOpenmbvOK   else "1"
    ret+="0" if ds.guiTestHdf5serieOK is None or ds.guiTestHdf5serieOK else "1"
    ret+="0" if ds.guiTestMbsimguiOK  is None or ds.guiTestMbsimguiOK  else "1"
    return ret

  def colData_ref(self, ds):
    allowedUser=self.gh.getUserInMbsimenvOrg(base.helper.GithubCache.viewTimeout)
    refUrl=django.urls.reverse('runexamples:compareresult', args=[ds.id])
    updateUrl=django.urls.reverse('runexamples:ref_update', args=[urllib.parse.quote(ds.exampleName, safe="")])
    dsStatic=self.getStaticDS(ds)
    checked='checked="checked"' if dsStatic is not None and dsStatic.update else ""
    refCheckbox='<span class="float-right">[<input type="checkbox" onClick="changeRefUpdate($(this), \'%s\', \'%s\');" %s/>]</span>'%\
                (updateUrl, ds.exampleName, checked) if self.isCurrent and allowedUser else ""
    if ds.results.count()==0:
      ret='<span class="float-left"><span class="text-warning">%s</span>&nbsp;no reference</span>%s'%\
          (octicon("alert"), refCheckbox)
    elif ds.results.filterFailed().count()==0:
      ret='<span class="float-left"><span class="text-success">%s</span>&nbsp;<a href="%s">passed '\
          '<span class="badge badge-secondary">%d</span></a></span>'%(octicon("check"), refUrl, ds.results.count())
    else:
      ret='<span class="float-left"><span class="text-danger">%s</span>&nbsp;<a href="%s">failed '\
          '<span class="badge badge-secondary">%d</span> of <span class="badge badge-secondary">%d</span></a></span>%s'%\
          (octicon("stop"), refUrl, ds.results.filterFailed().count(), ds.results.count(), refCheckbox)
    return ret
  def colClass_ref(self, ds):
    if ds.results.count()==0:
      return 'table-warning'
    elif ds.results.filterFailed().count()==0:
      return 'table-success'
    else:
      return 'table-danger'
  def colSortKey_ref(self, ds):
    if ds.results.count()==0:
      return '1'
    elif ds.results.filterFailed().count()==0:
      return '0'
    else:
      return '2'

  def colData_webApp(self, ds):
    ret=""
    enabled="" if self.isCurrent else 'disabled="disabled"'
    url="mfmf"#"/mbsim/html/noVNC/mbsimwebapp.html?"+urllib.parse.urlencode(ombv, doseq=True)
    vis="visible" if ds.webappOpenmbv else "hidden"
    img=django.templatetags.static.static("base/openmbv.svg")
    ret+='<a href="%s"><button %s type="button" class="btn btn-outline-primary btn-xs" style="visibility:%s;">'\
         '<img src="%s" alt="ombv"/></button></a>&nbsp;'%(url, enabled, vis, img)
    url="mfmf"
    vis="visible" if ds.webappHdf5serie else "hidden"
    img=django.templatetags.static.static("base/h5plotserie.svg")
    ret+='<a href="%s"><button %s type="button" class="btn btn-outline-primary btn-xs" style="visibility:%s;">'\
         '<img src="%s" alt="h5p"/></button></a>&nbsp;'%(url, enabled, vis, img)
    url="mfmf"
    vis="visible" if ds.webappMbsimgui else "hidden"
    img=django.templatetags.static.static("base/mbsimgui.svg")
    ret+='<a href="%s"><button %s type="button" class="btn btn-outline-primary btn-xs" style="visibility:%s;">'\
         '<img src="%s" alt="gui"/></button></a>'%(url, enabled, vis, img)
    return ret
  def colSortKey_webApp(self, ds):
    return "%d%d%d"%(ds.webappOpenmbv, ds.webappHdf5serie, ds.webappMbsimgui)

  def colData_dep(self, ds):
    if ds.deprecatedNr is not None and ds.deprecatedNr>0:
      url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "Example", ds.id, "runOutput"])
      return octicon("alert")+'&nbsp;<a href="%s"><span class="badge badge-secondary">%d</span> found</a></td>'%\
        (url, nrDeprecated)
    else:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;none'
  def colClass_dep(self, ds):
    if ds.deprecatedNr is not None and ds.deprecatedNr>0:
      return 'table-warning'
    else:
      return 'table-success'
  def colSortKey_dep(self, ds):
    return ds.deprecatedNr

  def colData_xmlOut(self, ds):
    if ds.xmlOutputs.count()==0:
      return ""
    if ds.xmlOutputs.filterFailed().count()==0:
      icon='<span class="text-success">'+octicon("check")+'</span>'
      text="valid"
    else:
      icon='<span class="text-danger">'+octicon("stop")+'</span>'
      text="failed"
    url=django.urls.reverse('runexamples:xmloutput', args=[ds.id])
    return '%s&nbsp;<a href="%s">%s<span class="badge badge-secondary">%d</span></a>'%(icon, url, text, ds.xmlOutputs.count())
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

  # return the "data", "sort key" and "class" for columns ["data":required; "sort key" and "class":optional]

  def colData_kind(self, ds):
    return "<h5>"+ds.kind+"</h5>"+'''
      <div class="dropdown">
        <button class="btn btn-secondary btn-xs" type="button" id="calledCommandID" data-toggle="dropdown">
          Show suppression {}
        </button>
        <pre class="dropdown-menu" style="padding-left: 0.5em; padding-right: 0.5em;">{}</pre>
      </div>'''.format(octicon("triangle-down"), ds.suppressionRawText)
  def colSort_kind(self, ds):
    return str(self.isLeak(ds))+"_"+ds.kind
  def colClass_kind(self, ds):
    return 'table-warning' if self.isLeak(ds) else "table-danger"

  def colData_detail(self, ds):
    ret=""
    for ws in ds.whatsAndStacks.order_by("nr"):
      ret+='<h5 class="text-danger">'+ws.what+'</h5>'
      ret+='''
        <table id="{}" data-url="{}" class="table table-striped table-hover table-bordered table-sm">
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
    ret=""
    if ds.dir!="": ret+=ds.dir+"/"
    if ds.file!="": ret+=ds.file
    if ds.line is not None: ret+=":"+str(ds.line)
    return ret

  def colData_function(self, ds):
    return ds.fn

  def colData_library(self, ds):
    return ds.obj

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
    return ds.filename

  def colData_result(self, ds):
    url=django.urls.reverse('base:textFieldFromDB', args=["runexamples", "XMLOutput", ds.id, "resultOutput"])
    if ds.resultOK:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;<a href="%s">passed</a>'%(url)
    else:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)

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
    self.results=runexamples.models.Example.objects.get(id=self.kwargs["id"]).results

  # return the queryset to display [required]
  def queryset(self):
    return self.results

  # return the field name in the dataset using for search/filter [required]
  def searchField(self):
    return "h5Filename"

  # return the "data", "sort key" and "class" for columns ["data":required; "sort key" and "class":optional]

  def colData_h5file(self, ds):
    return ds.h5Filename

  def colData_dataset(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[file not in cur]'
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINREF:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[file not in ref]'
    return ds.dataset
  def colClass_dataset(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR or ds.result==runexamples.models.CompareResult.Result.FILENOTINREF:
      return 'table-danger'
    return ''

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
      return ''
    if ds.result==runexamples.models.CompareResult.Result.DATASETNOTINCUR or ds.result==runexamples.models.CompareResult.Result.DATASETNOTINREF:
      return 'table-danger'
    return ''

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
    if ds.result==runexamples.models.CompareResult.Result.LABELDIFFER:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;[label missing]'
    if ds.result==runexamples.models.CompareResult.Result.PASSED:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;passed'
    url=django.urls.reverse('runexamples:differenceplot', args=[ds.id])
    return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)
  def colClass_result(self, ds):
    if ds.result==runexamples.models.CompareResult.Result.FILENOTINCUR or ds.result==runexamples.models.CompareResult.Result.FILENOTINREF or \
       ds.result==runexamples.models.CompareResult.Result.DATASETNOTINCUR or ds.result==runexamples.models.CompareResult.Result.DATASETNOTINREF:
      return ''
    if ds.result==runexamples.models.CompareResult.Result.LABELNOTINCUR or ds.result==runexamples.models.CompareResult.Result.LABELNOTINREF or \
       ds.result==runexamples.models.CompareResult.Result.LABELDIFFER or ds.result==runexamples.models.CompareResult.Result.LABELDIFFER:
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
  with compareResult.h5File_open("rb") as djangoF:
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
    exampleStatic=runexamples.models.ExampleStatic.objects.get(exampleName=compareResult.example.exampleName)
    for r in exampleStatic.references.all():
      if r.h5FileName==compareResult.h5FileName:
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
      relErr=absErr/ref
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
