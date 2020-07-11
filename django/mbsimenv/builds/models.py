import django
import re

class RunManager(django.db.models.Manager):
  # return the current Run object for buildType (the one with the newest id)
  def getCurrent(self, buildType):
    run_id=self.filter(buildType=buildType).\
           aggregate(django.db.models.Max('id'))["id__max"]
    if run_id:
      return Run.objects.get(id=run_id)
    else:
      return None

  # return a queryset with all failed runs
  def filterFailed(self):
    return self.filter(
      (django.db.models.Q(fmatvecUpdateOK__isnull=False)   & django.db.models.Q(fmatvecUpdateOK=False)) |
      (django.db.models.Q(hdf5serieUpdateOK__isnull=False) & django.db.models.Q(hdf5serieUpdateOK=False)) |
      (django.db.models.Q(openmbvUpdateOK__isnull=False)   & django.db.models.Q(openmbvUpdateOK=False)) |
      (django.db.models.Q(mbsimUpdateOK__isnull=False)     & django.db.models.Q(mbsimUpdateOK=False)) |
      (django.db.models.Q(distributionOK__isnull=False)    & django.db.models.Q(distributionOK=False)) |
      django.db.models.Q(toolsFailed__gt=0)
    ).distinct()

class Run(django.db.models.Model):
  objects=RunManager()

  id=django.db.models.AutoField(primary_key=True)
  buildType=django.db.models.CharField(max_length=50)
  command=django.db.models.TextField()
  startTime=django.db.models.DateTimeField()
  endTime=django.db.models.DateTimeField(null=True, blank=True)
  fmatvecBranch=django.db.models.CharField(max_length=50)
  hdf5serieBranch=django.db.models.CharField(max_length=50)
  openmbvBranch=django.db.models.CharField(max_length=50)
  mbsimBranch=django.db.models.CharField(max_length=50)
  fmatvecUpdateOK=django.db.models.BooleanField(null=True, blank=True)
  hdf5serieUpdateOK=django.db.models.BooleanField(null=True, blank=True)
  openmbvUpdateOK=django.db.models.BooleanField(null=True, blank=True)
  mbsimUpdateOK=django.db.models.BooleanField(null=True, blank=True)
  fmatvecUpdateOutput=django.db.models.TextField()
  hdf5serieUpdateOutput=django.db.models.TextField()
  openmbvUpdateOutput=django.db.models.TextField()
  mbsimUpdateOutput=django.db.models.TextField()
  fmatvecUpdateTooltip=django.db.models.TextField()
  hdf5serieUpdateTooltip=django.db.models.TextField()
  openmbvUpdateTooltip=django.db.models.TextField()
  mbsimUpdateTooltip=django.db.models.TextField()
  fmatvecUpdateCommitID=django.db.models.CharField(max_length=50)
  hdf5serieUpdateCommitID=django.db.models.CharField(max_length=50)
  openmbvUpdateCommitID=django.db.models.CharField(max_length=50)
  mbsimUpdateCommitID=django.db.models.CharField(max_length=50)
  fmatvecUpdateMsg=django.db.models.CharField(max_length=100)
  hdf5serieUpdateMsg=django.db.models.CharField(max_length=100)
  openmbvUpdateMsg=django.db.models.CharField(max_length=100)
  mbsimUpdateMsg=django.db.models.CharField(max_length=100)
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
    return Run.objects.getCurrent(self.buildType)
  def getNext(self):
    id=Run.objects.filter(buildType=self.buildType,
                          id__gt=self.id).\
       aggregate(django.db.models.Min('id'))["id__min"]
    return self if id is None else Run.objects.get(id=id)
  def getPrevious(self):
    id=Run.objects.filter(buildType=self.buildType,
                          id__lt=self.id).\
       aggregate(django.db.models.Max('id'))["id__max"]
    return self if id is None else Run.objects.get(id=id)

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
    return self.filter(django.db.models.Q(willFail=False) & (
      (django.db.models.Q(configureOK__isnull=False) & django.db.models.Q(configureOK=False)) |
      (django.db.models.Q(makeOK__isnull=False)      & django.db.models.Q(makeOK=False)) |
      (django.db.models.Q(makeCheckOK__isnull=False) & django.db.models.Q(makeCheckOK=False)) |
      (django.db.models.Q(docOK__isnull=False)       & django.db.models.Q(docOK=False)) |
      (django.db.models.Q(xmldocOK__isnull=False)    & django.db.models.Q(xmldocOK=False))
    ))

class Tool(django.db.models.Model):
  objects=ToolManager()

  id=django.db.models.AutoField(primary_key=True)
  run=django.db.models.ForeignKey(Run, on_delete=django.db.models.CASCADE, related_name='tools')
  toolName=django.db.models.CharField(max_length=200)
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
