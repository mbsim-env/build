import django
import base.views

app_name="base"

urlpatterns = [
  django.urls.path('impressum_disclaimer_datenschutz/', base.views.Impressum.as_view(), name='impressum'),
  django.urls.path('listOcticons/', base.views.ListOcticons.as_view(), name='list_octicons'),
  django.urls.path('textFieldFromDB/<str:app>/<str:model>/<slug:id>/<str:field>/',
    base.views.TextFieldFromDB.as_view(), name='textFieldFromDB'),
  django.urls.path('textFieldFromDBDownload/<str:app>/<str:model>/<slug:id>/<str:field>/',
    base.views.textFieldFromDBDownload, name='textFieldFromDBDownload'),
  django.urls.path('fileDownloadFromDB/<str:app>/<str:model>/<slug:id>/<str:field>/',
    base.views.fileDownloadFromDB, name='fileDownloadFromDB'),
]
