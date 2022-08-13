import django
import builds.views

app_name="builds"

urlpatterns = [
  django.urls.path('run/current/<str:buildtype>/<str:fmatvecBranch>/<str:hdf5serieBranch>/<str:openmbvBranch>/<str:mbsimBranch>/',
    builds.views.currentBuildtypeBranch, name='current_buildtype_branch'),
  django.urls.path('run/current/<str:buildtype>/<str:fmatvecBranch>/<str:hdf5serieBranch>/<str:openmbvBranch>/<str:mbsimBranch>/distributionFile/',
    builds.views.runDistributionFileBuildtypeBranch),
  django.urls.path('run/current/<str:buildtype>/<str:fmatvecBranch>/<str:hdf5serieBranch>/<str:openmbvBranch>/<str:mbsimBranch>/distributionDebugFile/',
    builds.views.runDistributionDebugFileBuildtypeBranch),
  django.urls.path('run/<int:id>/', builds.views.Run.as_view(), name='run'),
  django.urls.path('run/<int:id>/distributionFile/', builds.views.runDistributionFileID), # relpath distributionFile is used (This URL is used hardcoded in webapprun!!!)
  django.urls.path('run/<int:id>/distributionDebugFile/', builds.views.runDistributionDebugFileID), # relpath distributionDebugFile is used
  django.urls.path('createUniqueRunID/<str:buildtype>/<str:executorID>/<str:fmatvecSHA>/<str:hdf5serieSHA>/<str:openmbvSHA>/<str:mbsimSHA>/<int:fmatvecTriggered>/<int:hdf5serieTriggered>/<int:openmbvTriggered>/<int:mbsimTriggered>/', builds.views.createUniqueRunID, name='createUniqueRunID'),
  django.urls.path('datatable/tool/<int:run_id>/', builds.views.DataTableTool.as_view(), name='datatable_tool'),
  django.urls.path('releaseDistribution/<int:run_id>/', builds.views.releaseDistribution, name='releaseDistribution'),
]
