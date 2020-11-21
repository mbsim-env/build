import django
import home.views

app_name="home"

urlpatterns = [
  django.urls.path('<path:suburl>', home.views.Home.as_view(), name='home'),
]
