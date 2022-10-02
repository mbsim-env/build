import django
import os
import re
from base.helper import addFieldLabel as AL
from base.helper import FieldLabel as L

class CIBranches(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  fmatvecBranch=AL(django.db.models.CharField(max_length=50), L.list, L.search)
  hdf5serieBranch=AL(django.db.models.CharField(max_length=50), L.list, L.search)
  openmbvBranch=AL(django.db.models.CharField(max_length=50), L.list, L.search)
  mbsimBranch=AL(django.db.models.CharField(max_length=50), L.list, L.search)
  class Meta:
    constraints=[
      django.db.models.UniqueConstraint(fields=['fmatvecBranch', 'hdf5serieBranch', 'openmbvBranch', 'mbsimBranch'],
                                        name="unique_ci_banches"),
    ]

class CIQueue(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  recTime=django.db.models.DateTimeField()
  fmatvecBranch=AL(django.db.models.CharField(blank=True, max_length=50), L.list, L.search)
  hdf5serieBranch=AL(django.db.models.CharField(blank=True, max_length=50), L.list, L.search)
  openmbvBranch=AL(django.db.models.CharField(blank=True, max_length=50), L.list, L.search)
  mbsimBranch=AL(django.db.models.CharField(blank=True, max_length=50), L.list, L.search)
  buildCommitID=django.db.models.CharField(blank=True, max_length=50)

class DailyBranches(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  fmatvecBranch=AL(django.db.models.CharField(max_length=50), L.list, L.search)
  hdf5serieBranch=AL(django.db.models.CharField(max_length=50), L.list, L.search)
  openmbvBranch=AL(django.db.models.CharField(max_length=50), L.list, L.search)
  mbsimBranch=AL(django.db.models.CharField(max_length=50), L.list, L.search)
  class Meta:
    constraints=[
      django.db.models.UniqueConstraint(fields=['fmatvecBranch', 'hdf5serieBranch', 'openmbvBranch', 'mbsimBranch'],
                                        name="unique_daily_banches"),
    ]

class Release(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  platform=AL(django.db.models.CharField(max_length=50), L.list)
  createDate=AL(django.db.models.DateField(), L.list)
  versionMajor=AL(django.db.models.PositiveSmallIntegerField(), L.list)
  versionMinor=AL(django.db.models.PositiveSmallIntegerField(), L.list)

  releaseFile=django.db.models.FileField(null=True, blank=True, max_length=100)
  @property
  def releaseFileName(self):
    if not self.releaseFile: return None
    return re.sub("^service_release_[0-9]+_", "", self.releaseFile.name)
  @releaseFileName.setter
  def releaseFileName(self, filename):
    if self.id is None:
      self.save()
    self.releaseFile.name="service_release_"+str(self.id)+"_"+filename

  releaseDebugFile=django.db.models.FileField(null=True, blank=True, max_length=100)
  @property
  def releaseDebugFileName(self):
    if not self.releaseDebugFile: return None
    return re.sub("^service_release_[0-9]+_", "", self.releaseDebugFile.name)
  @releaseDebugFileName.setter
  def releaseDebugFileName(self, filename):
    if self.id is None:
      self.save()
    self.releaseDebugFile.name="service_release_"+str(self.id)+"_"+filename

  class Meta:
    constraints=[
      django.db.models.UniqueConstraint(fields=['platform', 'versionMajor', 'versionMinor'], name="unique_releases"),
    ]

# delete all files referenced in Release when a Release object is deleted
def releaseDeleteHandler(sender, **kwargs):
  rel=kwargs["instance"]
  if rel.releaseFile:
    rel.releaseFile.delete(False)
  if rel.releaseDebugFile:
    rel.releaseDebugFile.delete(False)
django.db.models.signals.pre_delete.connect(releaseDeleteHandler, sender=Release)

class ManualManager(django.db.models.Manager):
  # return a queryset with all failed manuals
  def filterFailed(self):
    return self.filter(resultOK=False)

class Manual(django.db.models.Model):
  objects=ManualManager()

  id=django.db.models.CharField(primary_key=True, max_length=50)
  manualName=AL(django.db.models.CharField(max_length=100), L.list, L.search)
  resultOK=django.db.models.BooleanField()
  resultOutput=django.db.models.TextField(True)
  manualFile=django.db.models.FileField(max_length=100)
  @property
  def manualFileName(self):
    if not self.manualFile: return None
    return re.sub("^service_manual_[a-zA-Z0-9-_]+__", "", self.manualFile.name)
  @manualFileName.setter
  def manualFileName(self, filename):
    if self.id is None:
      self.save()
    self.manualFile.name="service_manual_"+str(self.id)+"__"+filename

# delete all files referenced in Manual when a Manual object is deleted
def manualDeleteHandler(sender, **kwargs):
  man=kwargs["instance"]
  if man.manualFile:
    man.manualFile.delete(False)
django.db.models.signals.pre_delete.connect(manualDeleteHandler, sender=Manual)

# only one row in this model exists!!!
class Info(django.db.models.Model):
  id=django.db.models.CharField(primary_key=True, max_length=50) # the git commit ID
  shortInfo=django.db.models.TextField() # container, image, git ID as text
  longInfo=django.db.models.TextField() # log file of automatic docker build
  buildImageID=django.db.models.CharField(max_length=100) # the image ID of "mbsimenv/build" used at the last ci build
  buildwin64ImageID=django.db.models.CharField(max_length=100) # the image ID of "mbsimenv/buildwin64" used at the last ci build
