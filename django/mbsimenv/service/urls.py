import base
import service.views

app_name="service"

urlpatterns = [
  base.helper.urls_path('home/', service.views.Home.as_view(), name='home'),
  base.helper.urls_path('docu/', service.views.Docu.as_view(), name='docu'),
  base.helper.urls_path('editbranches/<str:model>/', service.views.EditBranches.as_view(), name='editbranches'),
  base.helper.urls_path('latestbranchcombibuilds/<str:model>/', service.views.LatestBranchCombiBuilds.as_view(), name='latestbranchcombibuilds'),
  base.helper.urls_path('datatable/latestbranchcombibuilds/<str:model>/', service.views.DataTableLatestBranchCombiBuilds.as_view(), name='datatable_latestbranchcombibuilds'),
  base.helper.urls_path('feed/', service.views.Feed(), name='feed'),
  base.helper.urls_path('releases/', service.views.Releases.as_view(), name='releases'),
  base.helper.urls_path('releases/<str:filename>', service.views.releaseFile, name='releaseFile'),
  base.helper.urls_path('releases/current/<str:platform>/', service.views.currentReleaseFile, name='currentReleaseFile'),
  base.helper.urls_path('releases/current/debug/<str:platform>/', service.views.currentReleaseDebugFile, name='currentReleaseDebugFile'),
  base.helper.urls_path('datatable/editbranches/<str:model>/', service.views.DataTableEditBranches.as_view(), name='datatable_editbranches'),
  base.helper.urls_path('github/repobranches/', service.views.repoBranches, name='github_repobranches', robots=False),
  base.helper.urls_path('github/webhook/', service.views.webhook, robots=False),
  base.helper.urls_path('db/getbranchcombi/<str:model>/', service.views.getBranchCombination, name='db_getbranchcombi', robots=False),
  base.helper.urls_path('db/addbranchcombi/<str:model>/', service.views.addBranchCombination, name='db_addbranchcombi', robots=False),
  base.helper.urls_path('db/deletebranchcombi/<str:model>/<int:id>/', service.views.deleteBranchCombination, name='db_deletebranchcombi', robots=False),
  base.helper.urls_path('builds/current/<str:buildtype>/nrAll.svg', service.views.currentBuildNrAll,
    name='current_build_nrall'),
  base.helper.urls_path('builds/current/<str:buildtype>/nrFailed.svg', service.views.currentBuildNrFailed,
    name='current_build_nrfailed'),
  base.helper.urls_path('runexamples/current/<str:buildtype>/nrAll.svg', service.views.currentRunexampleNrAll,
    name='current_runexample_nrall'),
  base.helper.urls_path('runexamples/current/<str:buildtype>/nrFailed.svg', service.views.currentRunexampleNrFailed,
    name='current_runexample_nrfailed'),
  base.helper.urls_path('runexamples/current/<str:buildtype>/coverageRate.svg', service.views.currentCoverageRate,
    name='current_runexample_coveragerate'),
  base.helper.urls_path('manuals/nrAll.svg', service.views.manualsNrAll, name='manuals_nrall'),
  base.helper.urls_path('manuals/nrFailed.svg', service.views.manualsNrFailed, name='manuals_nrfailed'),
  base.helper.urls_path("webapp/", service.views.Webapp.as_view(), name="webapp"),
  base.helper.urls_path("checkvaliduser/", service.views.checkValidUser),
  base.helper.urls_path("filtergithubfeed/", service.views.filterGithubFeed, name="filtergithubfeed"),
  base.helper.urls_path("createfiltergithubfeed/", service.views.CreateFilterGitHubFeed.as_view(), name="createfiltergithubfeed"),
]
