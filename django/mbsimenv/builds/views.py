import django
import django.shortcuts
import builds
import base.views
import functools
import runexamples
from octicons.templatetags.octicons import octicon

# maps the current url to the proper run id url (without forwarding to keep the URL in the browser)
def currentBuildtype(request, buildtype):
  run=builds.models.Run.objects.getCurrent(buildtype)
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
      return django.shortcuts.redirect('builds:current_buildtype', self.run.buildType) # use the special current URL in browser
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)

    # get the corresponding examplerun ID to this build ID
    # and check if all these examples have passed or not
    examples=[]
    examplesAllOK=True
    if hasattr(self.run, "examples") and self.run.examples:
      for er in self.run.examples.all():
        ok=er.examples.filterFailed().count()==0
        examples.append({"id": er.id, "ok": ok, "buildType": er.buildType})
        if not ok: examplesAllOK=False

    context['run']=self.run
    # just a list which can be used to loop over in the template
    context['repoList']=["fmatvec", "hdf5serie", "openmbv", "mbsim"]
    context['examples']=examples
    context['examplesAllOK']=examplesAllOK
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
    return ds.toolName.replace("/", "/\u200b")
  def colSortKey_tool(self, ds):
    return ds.toolName

  def colData_configure(self, ds):
    if ds.configureOK is None:
      return ""
    url=django.urls.reverse('base:textFieldFromDB', args=["builds", "Tool", ds.id, "configureOutput"])
    if ds.configureOK:
      return '<span class="text-success">'+octicon("check")+'</span>&nbsp;<a href="%s">passed</a>'%(url)
    else:
      return '<span class="text-danger">'+octicon("stop")+'</span>&nbsp;<a href="%s">failed</a>'%(url)
  def colSortKey_configure(self, ds):
    return ds.configureOK
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
    return ds.makeOK
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
    return ds.makeCheckOK
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
    return ds.docOK
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
    return ds.xmldocOK
  def colClass_xmldoc(self, ds):
    if ds.xmldocOK is None:
      return ""
    return "table-success" if ds.xmldocOK else "table-danger"
