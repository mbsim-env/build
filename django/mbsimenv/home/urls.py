import base
import home.views

app_name="home"

urlpatterns = [
  base.helper.urls_path('videos/', home.views.Videos.as_view(), name='videos'),
  base.helper.urls_path('<path:suburl>', home.views.Home.as_view(), name='base'),
]
