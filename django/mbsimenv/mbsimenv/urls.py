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
import base
import django.shortcuts
import base.views
import mbsimenv
import django.conf.urls.static
import importlib.util

urlpatterns = [
  base.helper.urls_path('', lambda _: django.shortcuts.redirect('home:base', "index.html")),
  base.helper.urls_path('robots.txt', base.views.robotsTXT),
  base.helper.urls_path('base/', django.urls.include('base.urls')),
  base.helper.urls_path('admin/', django.contrib.admin.site.urls, robots="recFalse"),
  base.helper.urls_path('accounts/locallogin/' , base.views.LocalLogin.as_view() , name="localloginpage" , robots="recFalse"),
  base.helper.urls_path('accounts/githublogin/', base.views.GitHubLogin.as_view(), name="githubloginpage", robots="recFalse"),
  base.helper.urls_path('accounts/logout/', base.views.userLogout, robots="recFalse"),
  base.helper.urls_path('accounts/profile/', base.views.UserProfile.as_view(), name='base_userprofile', robots="recFalse"),
  base.helper.urls_path('accounts/', django.urls.include('allauth.urls'), robots="recFalse"),
]
if importlib.util.find_spec("runexamples") is not None:
  urlpatterns.append(base.helper.urls_path('runexamples/', django.urls.include('runexamples.urls')))
if importlib.util.find_spec("builds") is not None:
 urlpatterns.append(base.helper.urls_path('builds/', django.urls.include('builds.urls')))
if importlib.util.find_spec("service") is not None:
  urlpatterns.append(base.helper.urls_path('service/', django.urls.include('service.urls')))
if importlib.util.find_spec("home") is not None:
  urlpatterns.append(base.helper.urls_path('home/', django.urls.include('home.urls')))
