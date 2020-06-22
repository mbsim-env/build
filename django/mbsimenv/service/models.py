import django
import os
import re

class CIBranches(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  fmatvecBranch=django.db.models.CharField(max_length=50)
  hdf5serieBranch=django.db.models.CharField(max_length=50)
  openmbvBranch=django.db.models.CharField(max_length=50)
  mbsimBranch=django.db.models.CharField(max_length=50)
  class Meta:
    constraints=[
      django.db.models.UniqueConstraint(fields=['fmatvecBranch', 'hdf5serieBranch', 'openmbvBranch', 'mbsimBranch'],
                                        name="unique_banches"),
    ]

class CIQueue(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  recTime=django.db.models.DateTimeField()
  fmatvecBranch=django.db.models.CharField(null=True, max_length=50)
  hdf5serieBranch=django.db.models.CharField(null=True, max_length=50)
  openmbvBranch=django.db.models.CharField(null=True, max_length=50)
  mbsimBranch=django.db.models.CharField(null=True, max_length=50)
  buildCommitID=django.db.models.CharField(null=True, max_length=50)

class Release(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  platform=django.db.models.CharField(max_length=50)
  createDate=django.db.models.DateField()
  versionMajor=django.db.models.PositiveSmallIntegerField()
  versionMinor=django.db.models.PositiveSmallIntegerField()

  releaseFile=django.db.models.FileField(null=True, max_length=100)
  @property
  def releaseFileName(self):
    if self.releaseFile is None: return None
    return re.sub("^service_release_[0-9]+_", "", self.releaseFile.name)
  @releaseFileName.setter
  def releaseFileName(self, filename):
    if self.id is None:
      self.save()
    self.releaseFile.name="service_release_"+str(self.id)+"_"+filename

  releaseDebugFile=django.db.models.FileField(null=True, max_length=100)
  @property
  def releaseDebugFileName(self):
    if self.releaseDebugFile is None: return None
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
  if rel.releaseFile is not None:
    rel.releaseFile.delete(False)
  if rel.releaseDebugFile is not None:
    rel.releaseDebugFile.delete(False)
django.db.models.signals.pre_delete.connect(releaseDeleteHandler, sender=Release)

class ManualManager(django.db.models.Manager):
  # return a queryset with all failed manuals
  def filterFailed(self):
    return self.filter(resultOK=False)

class Manual(django.db.models.Model):
  objects=ManualManager()

  id=django.db.models.CharField(primary_key=True, max_length=50)
  manualName=django.db.models.CharField(max_length=100)
  resultOK=django.db.models.BooleanField()
  resultOutput=django.db.models.TextField(True)
  manualFile=django.db.models.FileField(max_length=100)
  @property
  def manualFileName(self):
    if self.manualFile is None: return None
    return re.sub("^service_manual_[a-zA-Z0-9-_]+__", "", self.manualFile.name)
  @manualFileName.setter
  def manualFileName(self, filename):
    if self.id is None:
      self.save()
    self.manualFile.name="service_manual_"+str(self.id)+"__"+filename

# delete all files referenced in Manual when a Manual object is deleted
def manualDeleteHandler(sender, **kwargs):
  man=kwargs["instance"]
  if man.manualFile is not None:
    man.manualFile.delete(False)
django.db.models.signals.pre_delete.connect(manualDeleteHandler, sender=Manual)

class Info(django.db.models.Model):
  id=django.db.models.CharField(primary_key=True, max_length=50) # the git commit ID
  shortInfo=django.db.models.TextField()
  longInfo=django.db.models.TextField()
