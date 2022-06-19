import django
import re
from base.helper import addFieldLabel as AL
from base.helper import FieldLabel as L
from django.db.models import Q

class RunManager(django.db.models.Manager):
  # return the current Run object for buildType (the one with the newest id)
  def getCurrent(self, buildType=None, fmatvecBranch=None, hdf5serieBranch=None, openmbvBranch=None, mbsimBranch=None):
    args={}
    if buildType is not None: args["buildType"]=buildType
    if fmatvecBranch is not None: args["fmatvecBranch"]=fmatvecBranch
    if hdf5serieBranch is not None: args["hdf5serieBranch"]=hdf5serieBranch
    if openmbvBranch is not None: args["openmbvBranch"]=openmbvBranch
    if mbsimBranch is not None: args["mbsimBranch"]=mbsimBranch
    return self.filter(**args).order_by('-startTime').first()

  # return a queryset with all failed runs
  def filterFailed(self):
    return self.filter(
      (Q(fmatvecUpdateOK__isnull=False)   & Q(fmatvecUpdateOK=False)) |
      (Q(hdf5serieUpdateOK__isnull=False) & Q(hdf5serieUpdateOK=False)) |
      (Q(openmbvUpdateOK__isnull=False)   & Q(openmbvUpdateOK=False)) |
      (Q(mbsimUpdateOK__isnull=False)     & Q(mbsimUpdateOK=False)) |
      (Q(distributionOK__isnull=False)    & Q(distributionOK=False)) |
      Q(toolsFailed__gt=0)
    ).distinct()

class Run(django.db.models.Model):
  objects=RunManager()

  id=django.db.models.AutoField(primary_key=True)
  buildType=AL(django.db.models.CharField(max_length=50), L.inline, L.list)
  executor=django.db.models.TextField()
  command=django.db.models.TextField()
  startTime=AL(django.db.models.DateTimeField(), L.inline, L.list)
  endTime=django.db.models.DateTimeField(null=True, blank=True)
  fmatvecBranch=AL(django.db.models.CharField(max_length=50), L.inline, L.list, L.search)
  hdf5serieBranch=AL(django.db.models.CharField(max_length=50), L.inline, L.list, L.search)
  openmbvBranch=AL(django.db.models.CharField(max_length=50), L.inline, L.list, L.search)
  mbsimBranch=AL(django.db.models.CharField(max_length=50), L.inline, L.list, L.search)
  fmatvecTriggered=django.db.models.BooleanField(default=False)
  hdf5serieTriggered=django.db.models.BooleanField(default=False)
  openmbvTriggered=django.db.models.BooleanField(default=False)
  mbsimTriggered=django.db.models.BooleanField(default=False)
  fmatvecUpdateOK=django.db.models.BooleanField(null=True, blank=True)
  hdf5serieUpdateOK=django.db.models.BooleanField(null=True, blank=True)
  openmbvUpdateOK=django.db.models.BooleanField(null=True, blank=True)
  mbsimUpdateOK=django.db.models.BooleanField(null=True, blank=True)
  fmatvecUpdateOutput=django.db.models.TextField()
  hdf5serieUpdateOutput=django.db.models.TextField()
  openmbvUpdateOutput=django.db.models.TextField()
  mbsimUpdateOutput=django.db.models.TextField()
  fmatvecUpdateCommitID=django.db.models.CharField(max_length=50)
  hdf5serieUpdateCommitID=django.db.models.CharField(max_length=50)
  openmbvUpdateCommitID=django.db.models.CharField(max_length=50)
  mbsimUpdateCommitID=django.db.models.CharField(max_length=50)
  fmatvecUpdateMsg=django.db.models.CharField(max_length=100)
  hdf5serieUpdateMsg=django.db.models.CharField(max_length=100)
  openmbvUpdateMsg=django.db.models.CharField(max_length=100)
  mbsimUpdateMsg=django.db.models.CharField(max_length=100)
  fmatvecUpdateAuthor=django.db.models.CharField(max_length=30)
  hdf5serieUpdateAuthor=django.db.models.CharField(max_length=30)
  openmbvUpdateAuthor=django.db.models.CharField(max_length=30)
  mbsimUpdateAuthor=django.db.models.CharField(max_length=30)
  fmatvecUpdateDate=django.db.models.DateTimeField(null=True)
  hdf5serieUpdateDate=django.db.models.DateTimeField(null=True)
  openmbvUpdateDate=django.db.models.DateTimeField(null=True)
  mbsimUpdateDate=django.db.models.DateTimeField(null=True)
  # tools = related ForeignKey
  toolsFailed=django.db.models.PositiveIntegerField(default=0) # just a cached value for performance of filterFailed
  # examples = related ForeignKey
  distributionOK=django.db.models.BooleanField(null=True, blank=True)
  distributionOutput=django.db.models.TextField()
  distributionFile=django.db.models.FileField(null=True, blank=True, max_length=100)
  @property
  def distributionFileName(self):
    if self.distributionFile is None: return None
    return re.sub("^builds_Run_[0-9]+_", "", self.distributionFile.name)
  @distributionFileName.setter
  def distributionFileName(self, filename):
    if self.id is None:
      self.save()
    self.distributionFile.name="builds_Run_"+str(self.id)+"_"+filename
  distributionDebugFile=django.db.models.FileField(null=True, blank=True, max_length=100)
  @property
  def distributionDebugFileName(self):
    if self.distributionDebugFile is None: return None
    return re.sub("^builds_Run_[0-9]+_", "", self.distributionDebugFile.name)
  @distributionDebugFileName.setter
  def distributionDebugFileName(self, filename):
    if self.id is None:
      self.save()
    self.distributionDebugFile.name="builds_Run_"+str(self.id)+"_"+filename

  def getCurrent(self):
    return Run.objects.getCurrent(self.buildType, self.fmatvecBranch, self.hdf5serieBranch,
                                                  self.openmbvBranch, self.mbsimBranch)
  def getNext(self):
    ret=Run.objects.filter(buildType=self.buildType,
                      fmatvecBranch=self.fmatvecBranch,
                      hdf5serieBranch=self.hdf5serieBranch,
                      openmbvBranch=self.openmbvBranch,
                      mbsimBranch=self.mbsimBranch,
                      startTime__gt=self.startTime).\
                    order_by("startTime").first()
    if ret is None:
      return self
    return ret
  def getPrevious(self):
    ret=Run.objects.filter(buildType=self.buildType,
                      fmatvecBranch=self.fmatvecBranch,
                      hdf5serieBranch=self.hdf5serieBranch,
                      openmbvBranch=self.openmbvBranch,
                      mbsimBranch=self.mbsimBranch,
                      startTime__lt=self.startTime).\
                    order_by("-startTime").first()
    if ret is None:
      return self
    return ret

  def nrAll(self):
    # 4 from the run (git update) and all the tools
    return 4+(1 if self.distributionOK is not None else 0)+self.tools.count()

  def nrFailed(self):
    nr=self.tools.filterFailed().count()
    if self.fmatvecUpdateOK   is not None and not self.fmatvecUpdateOK:   nr+=1
    if self.hdf5serieUpdateOK is not None and not self.hdf5serieUpdateOK: nr+=1
    if self.openmbvUpdateOK   is not None and not self.openmbvUpdateOK:   nr+=1
    if self.mbsimUpdateOK     is not None and not self.mbsimUpdateOK:     nr+=1
    if self.distributionOK    is not None and not self.distributionOK:    nr+=1
    return nr

# delete all files referenced in Run when a Run object is deleted
def runDeleteHandler(sender, **kwargs):
  run=kwargs["instance"]
  if run.distributionFile is not None:
    run.distributionFile.delete(False)
  if run.distributionDebugFile is not None:
    run.distributionDebugFile.delete(False)
django.db.models.signals.pre_delete.connect(runDeleteHandler, sender=Run)

class ToolManager(django.db.models.Manager):
  # return a queryset with all failed tools of the current queryset
  def filterFailed(self):
    return self.filter(Q(willFail=False) & (
      (Q(configureOK__isnull=False) & Q(configureOK=False)) |
      (Q(makeOK__isnull=False)      & Q(makeOK=False)) |
      (Q(makeCheckOK__isnull=False) & Q(makeCheckOK=False)) |
      (Q(docOK__isnull=False)       & Q(docOK=False)) |
      (Q(xmldocOK__isnull=False)    & Q(xmldocOK=False))
    ))

class Tool(django.db.models.Model):
  objects=ToolManager()

  id=django.db.models.AutoField(primary_key=True)
  run=django.db.models.ForeignKey(Run, on_delete=django.db.models.CASCADE, related_name='tools')
  toolName=AL(django.db.models.CharField(max_length=200), L.inline, L.list, L.search)
  willFail=django.db.models.BooleanField()
  configureOK=django.db.models.BooleanField(null=True, blank=True)
  configureOutput=django.db.models.TextField(blank=True)
  makeOK=django.db.models.BooleanField(null=True, blank=True)
  makeOutput=django.db.models.TextField(blank=True)
  makeCheckOK=django.db.models.BooleanField(null=True, blank=True)
  makeCheckOutput=django.db.models.TextField(blank=True)
  docOK=django.db.models.BooleanField(null=True, blank=True)
  docOutput=django.db.models.TextField(blank=True)
  xmldocOK=django.db.models.BooleanField(null=True, blank=True)
  xmldocOutput=django.db.models.TextField(blank=True)
