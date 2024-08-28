import base
import base.views

app_name="base"

urlpatterns = [
  base.helper.urls_path('impressum_disclaimer_datenschutz/', base.views.Impressum.as_view(), name='impressum'),
  base.helper.urls_path('listOcticons/', base.views.ListOcticons.as_view(), name='list_octicons'),
  base.helper.urls_path('textFieldFromDB/<str:app>/<str:model>/<slug:id>/<str:field>/',
    base.views.TextFieldFromDB.as_view(), name='textFieldFromDB', robots=False),
  base.helper.urls_path('textFieldFromDBDownload/<str:app>/<str:model>/<slug:id>/<str:field>/',
    base.views.textFieldFromDBDownload, name='textFieldFromDBDownload', robots=False),
  base.helper.urls_path('fileDownloadFromDB/<str:app>/<str:model>/<slug:id>/<str:field>/',
    base.views.fileDownloadFromDB, name='fileDownloadFromDB', robots=False),
  base.helper.urls_path('fileDownloadFromDBMedia/<str:name>/',
    base.views.fileDownloadFromDBMedia, name='fileDownloadFromDBMedia', robots=False),
]
