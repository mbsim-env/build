import base
import runexamples.views

app_name="runexamples"

urlpatterns = [
  base.helper.urls_path('run/current/<str:buildtype>/', runexamples.views.currentBuildtype, name='current_buildtype', robots=False),
  base.helper.urls_path('run/current/<str:buildtype>/<str:fmatvecBranch>/<str:hdf5serieBranch>/<str:openmbvBranch>/<str:mbsimBranch>/',
    runexamples.views.currentBuildtypeBranch, name='current_buildtype_branch', robots=False),
  base.helper.urls_path('run/<int:id>/', runexamples.views.Run.as_view(), name='run', robots=False),
  base.helper.urls_path('valgrind/<int:id>/', runexamples.views.Valgrind.as_view(), name='valgrind', robots=False),
  base.helper.urls_path('xmloutput/<int:id>/', runexamples.views.XMLOutput.as_view(), name='xmloutput', robots=False),
  base.helper.urls_path('compareresult/<int:id>/', runexamples.views.CompareResult.as_view(), name='compareresult', robots=False),
  base.helper.urls_path('differenceplot/<int:id>/', runexamples.views.DifferencePlot.as_view(), name='differenceplot', robots=False),
  base.helper.urls_path('datatable/example/<int:run_id>/', runexamples.views.DataTableExample.as_view(), name='datatable_example', robots=False),
  base.helper.urls_path('datatable/valgrinderror/<int:id>/', runexamples.views.DataTableValgrindError.as_view(), name='datatable_valgrinderror', robots=False),
  base.helper.urls_path('datatable/valgrindstack/<int:id>/', runexamples.views.DataTableValgrindStack.as_view(), name='datatable_valgrindstack', robots=False),
  base.helper.urls_path('datatable/xmloutput/<int:id>/', runexamples.views.DataTableXMLOutput.as_view(), name='datatable_xmloutput', robots=False),
  base.helper.urls_path('datatable/compareresult/<int:id>/', runexamples.views.DataTableCompareResult.as_view(), name='datatable_compareresult', robots=False),
  base.helper.urls_path('db/refUpdate/<str:exampleName>/', runexamples.views.refUpdate, name='ref_update', robots=False),
  base.helper.urls_path('chart/differenceplot/<int:id>/', runexamples.views.chartDifferencePlot, name='chart_differenceplot', robots=False),
  base.helper.urls_path('allExampleStatic/', runexamples.views.allExampleStatic, name='allExampleStatic'),
  base.helper.urls_path('dirfilecoverage/<int:id>/', runexamples.views.DirFileCoverage.as_view(), name='dirfilecoverage', robots=False),
  base.helper.urls_path('filecoverage/<int:id>/<int:prefixIdx>/<str:absfile>/', runexamples.views.FileCoverage.as_view(), name='filecoverage', robots=False),
]
