import django
import service.views

app_name="service"

urlpatterns = [
  django.urls.path('home/', service.views.Home.as_view(), name='home'),
  django.urls.path('editbranches/<str:model>/', service.views.EditBranches.as_view(), name='editbranches'),
  django.urls.path('latestbranchcombibuilds/<str:model>/', service.views.LatestBranchCombiBuilds.as_view(), name='latestbranchcombibuilds'),
  django.urls.path('datatable/latestbranchcombibuilds/<str:model>/', service.views.DataTableLatestBranchCombiBuilds.as_view(), name='datatable_latestbranchcombibuilds'),
  django.urls.path('feed/', service.views.Feed(), name='feed'),
  django.urls.path('releases/', service.views.Releases.as_view(), name='releases'),
  django.urls.path('releases/<str:filename>', service.views.releaseFile, name='releaseFile'),
  django.urls.path('releases/current/<str:platform>/', service.views.currentReleaseFile, name='currentReleaseFile'),
  django.urls.path('releases/current/debug/<str:platform>/', service.views.currentReleaseDebugFile, name='currentReleaseDebugFile'),
  django.urls.path('datatable/editbranches/<str:model>/', service.views.DataTableEditBranches.as_view(), name='datatable_editbranches'),
  django.urls.path('github/repobranches/', service.views.repoBranches, name='github_repobranches'),
  django.urls.path('github/webhook/', service.views.webhook),
  django.urls.path('db/getbranchcombi/<str:model>/', service.views.getBranchCombination, name='db_getbranchcombi'),
  django.urls.path('db/addbranchcombi/<str:model>/', service.views.addBranchCombination, name='db_addbranchcombi'),
  django.urls.path('db/deletebranchcombi/<str:model>/<int:id>/', service.views.deleteBranchCombination, name='db_deletebranchcombi'),
  django.urls.path('builds/current/<str:buildtype>/nrAll.svg', service.views.currentBuildNrAll,
    name='current_build_nrall'),
  django.urls.path('builds/current/<str:buildtype>/nrFailed.svg', service.views.currentBuildNrFailed,
    name='current_build_nrfailed'),
  django.urls.path('runexamples/current/<str:buildtype>/nrAll.svg', service.views.currentRunexampleNrAll,
    name='current_runexample_nrall'),
  django.urls.path('runexamples/current/<str:buildtype>/nrFailed.svg', service.views.currentRunexampleNrFailed,
    name='current_runexample_nrfailed'),
  django.urls.path('runexamples/current/<str:buildtype>/coverageRate.svg', service.views.currentCoverageRate,
    name='current_runexample_coveragerate'),
  django.urls.path('manuals/nrAll.svg', service.views.manualsNrAll, name='manuals_nrall'),
  django.urls.path('manuals/nrFailed.svg', service.views.manualsNrFailed, name='manuals_nrfailed'),
  django.urls.path("webapp/", service.views.Webapp.as_view(), name="webapp"),
  django.urls.path("checkvaliduser/", service.views.checkValidUser),
  django.urls.path("filtergithubfeed/", service.views.filterGithubFeed, name="filtergithubfeed"),
  django.urls.path("createfiltergithubfeed/", service.views.CreateFilterGitHubFeed.as_view(), name="createfiltergithubfeed"),
]
