import django
import runexamples.views

app_name="runexamples"

urlpatterns = [
  django.urls.path('run/current/<str:buildtype>/', runexamples.views.currentBuildtype, name='current_buildtype'),
  django.urls.path('run/<int:id>/', runexamples.views.Run.as_view(), name='run'),
  django.urls.path('valgrind/<int:id>/', runexamples.views.Valgrind.as_view(), name='valgrind'),
  django.urls.path('xmloutput/<int:id>/', runexamples.views.XMLOutput.as_view(), name='xmloutput'),
  django.urls.path('compareresult/<int:id>/', runexamples.views.CompareResult.as_view(), name='compareresult'),
  django.urls.path('differenceplot/<int:id>/', runexamples.views.DifferencePlot.as_view(), name='differenceplot'),
  django.urls.path('datatable/example/<int:run_id>/', runexamples.views.DataTableExample.as_view(), name='datatable_example'),
  django.urls.path('datatable/valgrinderror/<int:id>/', runexamples.views.DataTableValgrindError.as_view(), name='datatable_valgrinderror'),
  django.urls.path('datatable/valgrindstack/<int:id>/', runexamples.views.DataTableValgrindStack.as_view(), name='datatable_valgrindstack'),
  django.urls.path('datatable/xmloutput/<int:id>/', runexamples.views.DataTableXMLOutput.as_view(), name='datatable_xmloutput'),
  django.urls.path('datatable/compareresult/<int:id>/', runexamples.views.DataTableCompareResult.as_view(), name='datatable_compareresult'),
  django.urls.path('db/refUpdate/<str:exampleName>/', runexamples.views.refUpdate, name='ref_update'),
  django.urls.path('chart/differenceplot/<int:id>/', runexamples.views.chartDifferencePlot, name='chart_differenceplot'),
  django.urls.path('allExampleStatic/', runexamples.views.allExampleStatic, name='allExampleStatic'),
]
