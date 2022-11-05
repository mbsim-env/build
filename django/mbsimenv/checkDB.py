#! /usr/bin/python3

# This script checks an existing database (local or buildSystem (postgres)).
# It lists unused rows in the database and unused files in the databasemedia.
# Most of the errors reported by this script are bugs in the mbsim-env/build repo.

import django
import os
import ast
import glob
import argparse
import paramiko
import builds
import runexamples
import service
import allauth

argparser=argparse.ArgumentParser(description="Check DB")
argBuildSystemRun=argparser.add_mutually_exclusive_group(required=True)
argBuildSystemRun.add_argument('--buildSystemRun', action='store_true', help='Run on "buildsystem".')
argBuildSystemRun.add_argument('--no-buildSystemRun', dest='buildSystemRun', action='store_false', help='Run locally, "localdocker" or "local".')
args=argparser.parse_args()
if args.buildSystemRun:
  os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
else:
  if os.path.isfile("/.dockerenv"):
    os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_localdocker"
  else:
    os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_local"
django.setup()
def rowID(row):
  return str(type(row))+" "+str(row.pk)



def walk(rows, allRefRows):
  for row in rows:
    allRefRows.add(rowID(row))
    for field in row._meta.get_fields():
      if isinstance(field, django.db.models.ManyToOneRel):
        walk(getattr(row, field.name).all(), allRefRows)
allRefRows=set()
walk(builds.models.Run.objects.all(), allRefRows)
walk(runexamples.models.Run.objects.all(), allRefRows)
walk(runexamples.models.ExampleStatic.objects.all(), allRefRows)
walk(service.models.Release.objects.all(), allRefRows)
walk(service.models.CIBranches.objects.all(), allRefRows)
walk(service.models.DailyBranches.objects.all(), allRefRows)
walk(service.models.CIQueue.objects.all(), allRefRows)
walk(service.models.Info.objects.all(), allRefRows)
walk(service.models.Manual.objects.all(), allRefRows)
walk(django.contrib.sessions.models.Session.objects.all(), allRefRows)
walk(django.contrib.admin.models.LogEntry.objects.all(), allRefRows)
walk(allauth.socialaccount.models.SocialToken.objects.all(), allRefRows)
print("referenced rows = ", len(allRefRows))



skipApp=set([
  "django.contrib.auth",
  "django.contrib.contenttypes",
  "django.contrib.sites",
])
allRows=set()
allRefFiles=set()
for app in django.apps.apps.get_app_configs():
  if app.name in skipApp:
    continue
  for model in app.get_models():
    for row in model.objects.all():
      allRows.add(rowID(row))
      for field in row._meta.get_fields():
        if isinstance(field, django.db.models.FileField):
          fieldFile=getattr(row, field.name)
          if fieldFile:
            allRefFiles.add(fieldFile.name)
print("all rows = ", len(allRows))
print("all referenced files = ", len(allRefFiles))



allFiles=set()
if django.conf.settings.DEFAULT_FILE_STORAGE=="mbsimenv.storage.SimpleSFTPStorage":
  params=django.conf.settings.SIMPLE_SFTP_STORAGE_PARAMS
  client=paramiko.client.SSHClient()
  client.set_missing_host_key_policy(paramiko.client.MissingHostKeyPolicy)
  client.connect(params["hostname"], port=params["port"],
                      username=params["username"], password=params["password"],
                      allow_agent=False, look_for_keys=False, timeout=60, banner_timeout=60, auth_timeout=60)
  sftp=client.open_sftp()
  try:
    for f in sftp.listdir(params["root"]):
      allFiles.add(f)
  finally:
    sftp.close()
    client.close()
elif django.conf.settings.DEFAULT_FILE_STORAGE=="django.core.files.storage.FileSystemStorage":
  for f in glob.glob(django.conf.settings.MEDIA_ROOT+"/*"):
    allFiles.add(os.path.basename(f))
print("all files = ", len(allFiles))



notRefRows=allRows-allRefRows
print("NOT referenced rows = ", len(notRefRows), ":")
for row in notRefRows:
  print(row)
notRefFiles=allFiles-allRefFiles
print("NOT referenced files = ", len(notRefFiles), ":")
for f in notRefFiles:
  print(f)
missingRefFiles=allRefFiles-allFiles
print("MISSING referenced files = ", len(missingRefFiles), ":")
for f in missingRefFiles:
  print(f)
