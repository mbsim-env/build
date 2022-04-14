import django
import builds.views

app_name="builds"

urlpatterns = [
  django.urls.path('run/current/<str:buildtype>/<str:fmatvecBranch>/<str:hdf5serieBranch>/<str:openmbvBranch>/<str:mbsimBranch>/',
    builds.views.currentBuildtypeBranch, name='current_buildtype_branch'),
  django.urls.path('run/<int:id>/', builds.views.Run.as_view(), name='run'),
  django.urls.path('run/<int:id>/distributionFile/', builds.views.runDistributionFile), # relpath distributionFile is used (This URL is used hardcoded in webapprun!!!)
  django.urls.path('run/<int:id>/distributionDebugFile/', builds.views.runDistributionDebugFile), # relpath distributionDebugFile is used
  django.urls.path('datatable/tool/<int:run_id>/', builds.views.DataTableTool.as_view(), name='datatable_tool'),
  django.urls.path('releaseDistribution/<int:run_id>/', builds.views.releaseDistribution, name='releaseDistribution'),
]
