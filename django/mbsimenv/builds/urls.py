import base
import builds.views

app_name="builds"

urlpatterns = [
  base.helper.urls_path('run/current/<str:buildtype>/<str:fmatvecBranch>/<str:hdf5serieBranch>/<str:openmbvBranch>/<str:mbsimBranch>/',
    builds.views.currentBuildtypeBranch, name='current_buildtype_branch', robots=False),
  base.helper.urls_path('run/current/<str:buildtype>/<str:fmatvecBranch>/<str:hdf5serieBranch>/<str:openmbvBranch>/<str:mbsimBranch>/distributionFile/',
    builds.views.runDistributionFileBuildtypeBranch, robots=False),
  base.helper.urls_path('run/current/<str:buildtype>/<str:fmatvecBranch>/<str:hdf5serieBranch>/<str:openmbvBranch>/<str:mbsimBranch>/distributionDebugFile/',
    builds.views.runDistributionDebugFileBuildtypeBranch, robots=False),
  base.helper.urls_path('run/<int:id>/', builds.views.Run.as_view(), name='run', robots=False),
  base.helper.urls_path('run/<int:id>/distributionFile/', builds.views.runDistributionFileID, robots=False), # relpath distributionFile is used (This URL is used hardcoded in webapprun!!!)
  base.helper.urls_path('run/<int:id>/distributionDebugFile/', builds.views.runDistributionDebugFileID, robots=False), # relpath distributionDebugFile is used
  base.helper.urls_path('createUniqueRunID/<str:buildtype>/<str:executorID>/<str:fmatvecSHA>/<str:hdf5serieSHA>/<str:openmbvSHA>/<str:mbsimSHA>/<int:fmatvecTriggered>/<int:hdf5serieTriggered>/<int:openmbvTriggered>/<int:mbsimTriggered>/', builds.views.createUniqueRunID, name='createUniqueRunID', robots=False),
  base.helper.urls_path('datatable/tool/<int:run_id>/', builds.views.DataTableTool.as_view(), name='datatable_tool', robots=False),
  base.helper.urls_path('releaseDistribution/<int:run_id>/', builds.views.releaseDistribution, name='releaseDistribution', robots=False),
]
