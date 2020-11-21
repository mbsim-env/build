"""mbsimenv URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import django
import django.shortcuts
import base.views
import mbsimenv
import django.conf.urls.static
import importlib.util

urlpatterns = [
  django.urls.path('', lambda _: django.shortcuts.redirect('service:home')),
  django.urls.path('base/', django.urls.include('base.urls')),
  django.urls.path('admin/', django.contrib.admin.site.urls),
  django.urls.path('accounts/login/', lambda _: django.shortcuts.redirect('github_login')),
  django.urls.path('accounts/logout/', base.views.userLogout),
  django.urls.path('accounts/profile/', base.views.UserProfile.as_view(), name='base_userprofile'),
]
if importlib.util.find_spec("runexamples") is not None:
  urlpatterns.append(django.urls.path('runexamples/', django.urls.include('runexamples.urls')))
if importlib.util.find_spec("builds") is not None:
 urlpatterns.append(django.urls.path('builds/', django.urls.include('builds.urls')))
if importlib.util.find_spec("service") is not None:
  urlpatterns.append(django.urls.path('service/', django.urls.include('service.urls')))
if importlib.util.find_spec("home") is not None:
  urlpatterns.append(django.urls.path('home/', django.urls.include('home.urls')))
if importlib.util.find_spec("allauth") is not None:
  urlpatterns.append(django.urls.path('accounts/', django.urls.include('allauth.urls')))
else:
  urlpatterns.append(django.urls.path('accounts/', django.views.defaults.permission_denied, name='account_login'))
