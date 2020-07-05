"""
Django settings for mbsimenv project.

Generated by 'django-admin startproject' using Django 3.0.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
import logging
import json
import base.helper
import mbsimenvSecrets
import importlib # mfmf use something different for a minimal install

DEBUG = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if "postgresPassword" not in mbsimenvSecrets.getSecrets() and not os.path.isfile("/.dockerenv"):
  MEDIA_ROOT = os.path.join(BASE_DIR, "media_root")
else:
  MEDIA_ROOT = "/databasemedia"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY=mbsimenvSecrets.getSecrets()["djangoSecretKey"]

# if debugging enabled python requests (urllib3) logging
if DEBUG:
  l=logging.getLogger("urllib3")
  l.setLevel(logging.DEBUG)
  l.addHandler(logging.StreamHandler())

ALLOWED_HOSTS = [os.environ.get("MBSIMENVSERVERNAME", ""), 'localhost', '127.0.0.1', '[::1]']


# Application definition

INSTALLED_APPS = [
  'base.apps.BaseConfig',
  'runexamples.apps.RunexamplesConfig',
  'builds.apps.BuildsConfig',
  'service.apps.ServiceConfig',
  'django.contrib.admin',
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.messages',
  'django.contrib.staticfiles',
  'django.contrib.sites',
]+\
([
  'allauth',
  'allauth.account',
  'allauth.socialaccount',
  'allauth.socialaccount.providers.github',
] if importlib.util.find_spec("allauth") is not None else [])+\
(['octicons'] if importlib.util.find_spec("octicons") is not None else [])

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mbsimenv.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mbsimenv.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

if "postgresPassword" not in mbsimenvSecrets.getSecrets() and not os.path.isfile("/.dockerenv"):
  DATABASES={
    'default': {
      'ENGINE': 'django.db.backends.sqlite3',
      'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
      'OPTIONS': {
        'timeout': 60,
      },
    }
  }
  SECURE_SSL_REDIRECT = False
else:
  DATABASES={
    'default': {
      'ENGINE': 'django.db.backends.postgresql',
      'NAME': 'mbsimenv-service-database',
      'USER': 'mbsimenvuser',
      'PASSWORD': mbsimenvSecrets.getSecrets()["postgresPassword"] if "postgresPassword" in mbsimenvSecrets.getSecrets() else "",
      'HOST': 'database',
      'PORT': '5432',
      'CONN_MAX_AGE': 30,
    }
  }
  SECURE_SSL_REDIRECT = True


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)

SITE_ID = 1

# Provider specific settings
ACCOUNT_UNIQUE_EMAIL = False
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'SCOPE': [
            'read:org',
            'public_repo',
            'user:email',
        ],
    }
}

SESSION_SERIALIZER = "base.helper.SessionSerializer"

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = '/var/www/html/static'
STATICFILES_DIRS = [
  os.path.join(BASE_DIR, "static"),
]

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = "origin"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
