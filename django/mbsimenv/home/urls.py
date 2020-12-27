import django
import home.views

app_name="home"

urlpatterns = [
  django.urls.path('videos/', home.views.Videos.as_view(), name='videos'),
  django.urls.path('<path:suburl>', home.views.Home.as_view(), name='base'),
]
