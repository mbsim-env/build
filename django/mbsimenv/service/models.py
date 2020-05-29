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

class Release(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  platform=django.db.models.CharField(max_length=50)
  createDate=django.db.models.DateField()
  versionMajor=django.db.models.PositiveSmallIntegerField()
  versionMinor=django.db.models.PositiveSmallIntegerField()
  releaseFile=django.db.models.FileField(null=True, max_length=100)
  @property
  def releaseFileName(self):
    return re.sub("^service_release_[0-9]+_", "", self.releaseFile.name)
  @releaseFileName.setter
  def releaseFileName(self, filename):
    if self.id is None:
      self.save()
    self.releaseFile.name="service_release_"+str(self.id)+"_"+filename
  class Meta:
    constraints=[
      django.db.models.UniqueConstraint(fields=['platform', 'versionMajor', 'versionMinor'], name="unique_releases"),
    ]

# delete all files referenced in Release when a Release object is deleted
def releaseDeleteHandler(sender, **kwargs):
  rel=kwargs["instance"]
  if rel is not None:
    rel.releaseFile.delete(False)
django.db.models.signals.pre_delete.connect(releaseDeleteHandler, sender=Release)

class ModelManager(django.db.models.Manager):
  # return a queryset with all failed manuals
  def filterFailed(self):
    return self.filter(resultOK=False)

class Manual(django.db.models.Model):
  objects=ModelManager()

  id=django.db.models.CharField(primary_key=True, max_length=50)
  manualName=django.db.models.CharField(max_length=100)
  resultOK=django.db.models.BooleanField()
  resultOutput=django.db.models.TextField(True)
  manualFile=django.db.models.FileField(max_length=100)
  @property
  def manualFileName(self):
    return re.sub("^service_manual_[a-zA-Z0-9-_]+__", "", self.manualFile.name)
  @manualFileName.setter
  def manualFileName(self, filename):
    if self.id is None:
      self.save()
    self.manualFile.name="service_manual_"+str(self.id)+"__"+filename

class Info(django.db.models.Model):
  id=django.db.models.CharField(primary_key=True, max_length=50) # the git commit ID
  shortInfo=django.db.models.TextField()
  longInfo=django.db.models.TextField()
