import django
import builds.models
import django.contrib.contenttypes.models
import django.contrib.contenttypes.fields
import re
import uuid
from base.helper import addFieldLabel as AL
from base.helper import FieldLabel as L
from django.db.models import Q

class RunManager(django.db.models.Manager):
  # return the current Run object for buildType (the one with the newest id)
  def getCurrent(self, buildType=None, fmatvecBranch=None, hdf5serieBranch=None, openmbvBranch=None, mbsimBranch=None):
    args={}
    if buildType is not None: args["buildType"]=buildType
    if fmatvecBranch is not None: args["build_run__fmatvecBranch"]=fmatvecBranch
    if hdf5serieBranch is not None: args["build_run__hdf5serieBranch"]=hdf5serieBranch
    if openmbvBranch is not None: args["build_run__openmbvBranch"]=openmbvBranch
    if mbsimBranch is not None: args["build_run__mbsimBranch"]=mbsimBranch
    return self.filter(**args).order_by('-startTime').first()

  # return a queryset with all failed runs
  def filterFailed(self):
    return self.filter(
      (Q(coverageOK__isnull=False)   & Q(coverageOK=False)) |
      Q(examplesFailed__gt=0)
    ).distinct()

class Run(django.db.models.Model):
  objects=RunManager()

  id=django.db.models.AutoField(primary_key=True)
  build_run=django.db.models.ForeignKey(builds.models.Run, null=True, blank=True, on_delete=django.db.models.SET_NULL, related_name="examples")
  buildType=AL(django.db.models.CharField(max_length=50), L.inline, L.list)
  executor=AL(django.db.models.TextField(), L.inline, L.list)
  command=django.db.models.TextField()
  startTime=AL(django.db.models.DateTimeField(), L.inline, L.list)
  endTime=django.db.models.DateTimeField(null=True, blank=True)
  # examples = related ForeignKey
  examplesFailed=django.db.models.PositiveIntegerField(default=0) # just a cached value for performance of filterFailed
  sourceDir=django.db.models.CharField(max_length=100, null=True, blank=True)
  coverageOK=django.db.models.BooleanField(null=True, blank=True)
  coverageRate=django.db.models.FloatField(null=True, blank=True)
  coverageOutput=django.db.models.TextField(blank=True)
  coverageFile=django.db.models.FileField(null=True, blank=True, max_length=200)
  @property
  def coverageFileName(self):
    if not self.coverageFile: return None
    return re.sub("^runexamples_Run_[0-9]+_", "", self.coverageFile.name)
  @coverageFileName.setter
  def coverageFileName(self, filename):
    if self.id is None:
      self.save()
    self.coverageFile.name="runexamples_Run_"+str(self.id)+"_"+filename

  def getCurrent(self):
    if self.build_run:
      return Run.objects.getCurrent(self.buildType, self.build_run.fmatvecBranch, self.build_run.hdf5serieBranch,
                                                    self.build_run.openmbvBranch, self.build_run.mbsimBranch)
    return Run.objects.getCurrent(self.buildType)
  def getNext(self):
    if self.build_run:
      ret=Run.objects.filter(buildType=self.buildType,
                        build_run__fmatvecBranch=self.build_run.fmatvecBranch,
                        build_run__hdf5serieBranch=self.build_run.hdf5serieBranch,
                        build_run__openmbvBranch=self.build_run.openmbvBranch,
                        build_run__mbsimBranch=self.build_run.mbsimBranch,
                        startTime__gt=self.startTime).\
                      order_by("startTime").first()
    else:
      ret=Run.objects.filter(buildType=self.buildType,
                        startTime__gt=self.startTime).\
                      order_by("startTime").first()
    if ret is None:
      return self
    return ret
  def getPrevious(self):
    if self.build_run:
      ret=Run.objects.filter(buildType=self.buildType,
                        build_run__fmatvecBranch=self.build_run.fmatvecBranch,
                        build_run__hdf5serieBranch=self.build_run.hdf5serieBranch,
                        build_run__openmbvBranch=self.build_run.openmbvBranch,
                        build_run__mbsimBranch=self.build_run.mbsimBranch,
                        startTime__lt=self.startTime).\
                      order_by("-startTime").first()
    else:
      ret=Run.objects.filter(buildType=self.buildType,
                        startTime__lt=self.startTime).\
                      order_by("-startTime").first()
    if ret is None:
      return self
    return ret

  def nrAll(self):
    nr=self.examples.count()
    if self.coverageOK is not None: nr=nr+1
    return nr

  def nrFailed(self):
    nr=self.examples.filterFailed().count()
    if self.coverageOK is not None and not self.coverageOK: nr=nr+1
    return nr

class ExampleManager(django.db.models.Manager):
  # return a queryset with all failed examples of the current queryset
  def filterFailed(self):
    return self.filter(Q(willFail=False) & (
      (Q(runResult__isnull=False)          & Q(runResult__in=[Example.RunResult.FAILED, Example.RunResult.WARNING])) |
      (Q(guiTestHdf5serieOK__isnull=False) & Q(guiTestHdf5serieOK=Example.GUITestResult.FAILED)) |
      (Q(guiTestOpenmbvOK__isnull=False)   & Q(guiTestOpenmbvOK=Example.GUITestResult.FAILED)) |
      (Q(guiTestMbsimguiOK__isnull=False)  & Q(guiTestMbsimguiOK=Example.GUITestResult.FAILED)) |
      (Q(deprecatedNr__isnull=False)       & Q(deprecatedNr__gt=0)) |
      Q(resultsFailed__gt=0) |
      Q(xmlOutputsFailed__gt=0)
    )).distinct()

class Example(django.db.models.Model):
  class RunResult(django.db.models.IntegerChoices):
    PASSED = 0
    FAILED = 1
    WARNING = 2
  class GUITestResult(django.db.models.IntegerChoices):
    PASSED = 0
    FAILED = 1
    WARNING = 2

  objects=ExampleManager()

  id=django.db.models.AutoField(primary_key=True)
  run=django.db.models.ForeignKey(Run, on_delete=django.db.models.CASCADE, related_name='examples')
  exampleName=AL(django.db.models.CharField(max_length=200), L.inline, L.list, L.search)
  willFail=django.db.models.BooleanField()
  runResult=django.db.models.IntegerField(null=True, blank=True, choices=RunResult.choices)
  runOutput=django.db.models.TextField(blank=True)
  # valgrinds = related ForeignKey
  time=django.db.models.DurationField(null=True, blank=True)
  guiTestHdf5serieOK=django.db.models.IntegerField(null=True, blank=True, choices=GUITestResult.choices)
  guiTestHdf5serieOutput=django.db.models.TextField(blank=True)
  guiTestOpenmbvOK=django.db.models.IntegerField(null=True, blank=True, choices=GUITestResult.choices)
  guiTestOpenmbvOutput=django.db.models.TextField(blank=True)
  guiTestMbsimguiOK=django.db.models.IntegerField(null=True, blank=True, choices=GUITestResult.choices)
  guiTestMbsimguiOutput=django.db.models.TextField(blank=True)
  # resultFiles = related ForeignKey
  resultsFailed=django.db.models.PositiveIntegerField(default=0) # just a cached value for performance of filterFailed
  webappHdf5serie=django.db.models.BooleanField()
  webappOpenmbv=django.db.models.BooleanField()
  webappMbsimgui=django.db.models.BooleanField()
  deprecatedNr=django.db.models.PositiveIntegerField(null=True, blank=True)
  # xmlOutputs = related ForeignKey
  xmlOutputsFailed=django.db.models.PositiveIntegerField(default=0) # just a cached value for performance of filterFailed

  def getCurrent(self):
    if self.run.build_run:
      return Example.objects.filter(run__buildType=self.run.buildType,
                               run__build_run__fmatvecBranch=self.run.build_run.fmatvecBranch,
                               run__build_run__hdf5serieBranch=self.run.build_run.hdf5serieBranch,
                               run__build_run__openmbvBranch=self.run.build_run.openmbvBranch,
                               run__build_run__mbsimBranch=self.run.build_run.mbsimBranch,
                               exampleName=self.exampleName).\
                             order_by("-startTime").first()
    else:
      return Example.objects.filter(run__buildType=self.run.buildType,
                               exampleName=self.exampleName).\
                             order_by("-startTime").first()
  def getNext(self):
    if self.run.build_run:
      ret=Example.objects.filter(run__buildType=self.run.buildType,
                            run__build_run__fmatvecBranch=self.run.build_run.fmatvecBranch,
                            run__build_run__hdf5serieBranch=self.run.build_run.hdf5serieBranch,
                            run__build_run__openmbvBranch=self.run.build_run.openmbvBranch,
                            run__build_run__mbsimBranch=self.run.build_run.mbsimBranch,
                            run__startTime__gt=self.run.startTime,
                            exampleName=self.exampleName).\
                          order_by("run__startTime").first()
    else:
      ret=Example.objects.filter(run__buildType=self.run.buildType,
                            run__startTime__gt=self.run.startTime,
                            exampleName=self.exampleName).\
                          order_by("run__startTime").first()
    if ret is None:
      return self
    return ret
  def getPrevious(self):
    if self.run.build_run:
      ret=Example.objects.filter(run__buildType=self.run.buildType,
                            run__build_run__fmatvecBranch=self.run.build_run.fmatvecBranch,
                            run__build_run__hdf5serieBranch=self.run.build_run.hdf5serieBranch,
                            run__build_run__openmbvBranch=self.run.build_run.openmbvBranch,
                            run__build_run__mbsimBranch=self.run.build_run.mbsimBranch,
                            run__startTime__lt=self.run.startTime,
                            exampleName=self.exampleName).\
                          order_by("-run__startTime").first()
    else:
      ret=Example.objects.filter(run__buildType=self.run.buildType,
                            run__startTime__lt=self.run.startTime,
                            exampleName=self.exampleName).\
                          order_by("-run__startTime").first()
    if ret is None:
      return self
    return ret

class XMLOutputManager(django.db.models.Manager):
  # return a queryset with all failed xmloutput of the current queryset
  def filterFailed(self):
    return self.filter(resultOK=False)

class XMLOutput(django.db.models.Model):
  objects=XMLOutputManager()

  id=django.db.models.AutoField(primary_key=True)
  example=django.db.models.ForeignKey(Example, on_delete=django.db.models.CASCADE, related_name='xmlOutputs')
  filename=AL(django.db.models.CharField(max_length=200), L.inline, L.list, L.search)
  resultOK=django.db.models.BooleanField()
  resultOutput=django.db.models.TextField()

class ExampleStatic(django.db.models.Model):
  exampleName=AL(django.db.models.CharField(max_length=200, primary_key=True), L.search)
  refTime=AL(django.db.models.DurationField(null=True, blank=True), L.list)
  update=AL(django.db.models.BooleanField(default=False), L.list)
  # references = related ForeignKey
  totalTimeNormal=AL(django.db.models.DurationField(null=True, blank=True), L.list) # total time of example run (without valgrind)
  totalTimeValgrind=AL(django.db.models.DurationField(null=True, blank=True), L.list) # total time of example run (with valgrind)
  queued=django.db.models.BooleanField(default=False)

class ExampleStaticReference(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  exampleStatic=django.db.models.ForeignKey(ExampleStatic, on_delete=django.db.models.CASCADE, related_name='references')
  h5File=AL(django.db.models.FileField(null=True, blank=True, max_length=200), L.inline, L.list, L.search)
  @property
  def h5FileName(self):
    if not self.h5File: return None
    return re.sub("^runexamples_ExampleStaticReference_[0-9]+_", "", self.h5File.name)
  @h5FileName.setter
  def h5FileName(self, filename):
    if self.id is None:
      self.save()
    self.h5File.name="runexamples_ExampleStaticReference_"+str(self.id)+"_"+filename
  h5FileSHA1=django.db.models.CharField(max_length=50)

# delete all files referenced in ExampleStaticReference when a ExampleStaticReference object is deleted
def exampleStaticReferenceDeleteHandler(sender, **kwargs):
  esr=kwargs["instance"]
  if esr.h5File:
    esr.h5File.delete(False)
django.db.models.signals.pre_delete.connect(exampleStaticReferenceDeleteHandler, sender=ExampleStaticReference)

class Valgrind(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  uuid=django.db.models.UUIDField(unique=True, default=uuid.uuid4, editable=False) # used for ForeignKey to enable bulk_create
  programType=AL(django.db.models.CharField(max_length=50), L.inline, L.list)
  programCmd=django.db.models.TextField()
  valgrindCmd=django.db.models.TextField()
  example=django.db.models.ForeignKey(Example, on_delete=django.db.models.CASCADE, related_name="valgrinds")
  # errors = related ForeignKey

class ValgrindError(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  uuid=django.db.models.UUIDField(unique=True, default=uuid.uuid4, editable=False) # used for ForeignKey to enable bulk_create

  valgrind=django.db.models.ForeignKey(Valgrind, on_delete=django.db.models.CASCADE, related_name="errors", to_field="uuid")
  kind=AL(django.db.models.CharField(max_length=100), L.inline, L.list)
  # whatsAndStacks = related ForeignKey
  suppressionRawText=django.db.models.TextField()

class ValgrindWhatAndStack(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  uuid=django.db.models.UUIDField(unique=True, default=uuid.uuid4, editable=False) # used for ForeignKey to enable bulk_create
  valgrindError=django.db.models.ForeignKey(ValgrindError, on_delete=django.db.models.CASCADE, related_name="whatsAndStacks", to_field="uuid")
  nr=django.db.models.PositiveSmallIntegerField() # defines the order of the "what" (and stack) entries
  what=AL(django.db.models.CharField(max_length=200), L.inline, L.list)
  # stacks = related ForeignKey
  class Meta:
    constraints=[
      django.db.models.UniqueConstraint(fields=['valgrindError', 'nr'], name="unique_orderPerError"),
    ]

class ValgrindFrame(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  whatAndStack=django.db.models.ForeignKey(ValgrindWhatAndStack, on_delete=django.db.models.CASCADE, related_name="stacks", to_field="uuid")
  nr=django.db.models.PositiveSmallIntegerField() # defines the order of the stack frame entries
  obj=django.db.models.CharField(max_length=250)
  fn=django.db.models.TextField() # a function name can be very long (templates)
  dir=AL(django.db.models.CharField(max_length=250), L.inline, L.list)
  file=AL(django.db.models.CharField(max_length=100), L.inline, L.list)
  line=AL(django.db.models.PositiveIntegerField(null=True, blank=True), L.inline, L.list)
  class Meta:
    constraints=[
      django.db.models.UniqueConstraint(fields=['whatAndStack', 'nr'], name="unique_orderPerStack"),
    ]

class CompareResultFile(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  uuid=django.db.models.UUIDField(unique=True, default=uuid.uuid4, editable=False) # used for ForeignKey to enable bulk_create
  example=django.db.models.ForeignKey(Example, on_delete=django.db.models.CASCADE, related_name='resultFiles')
  # results = related ForeignKey
  h5Filename=AL(django.db.models.CharField(max_length=100), L.inline, L.list, L.search) # must be consistent with h5FileName if set
  h5File=django.db.models.FileField(null=True, blank=True, max_length=200)
  @property
  def h5FileName(self):
    if not self.h5File: return None
    fn=re.sub("^runexamples_CompareResultFile_[0-9]+_", "", self.h5File.name)
    if fn!=self.h5Filename:
      raise RuntimeError("Filename missmatch in CompareResultFile.h5FileName[getter] id="+str(self.id)+" ("+self.h5File.name+" != "+self.h5Filename+")")
    return fn
  @h5FileName.setter
  def h5FileName(self, filename):
    if filename!=self.h5Filename:
      raise RuntimeError("Filename missmatch in CompareResultFile.h5FileName[setter] id="+str(self.id)+" ("+self.h5File.name+" != "+self.h5Filename+")")
    if self.id is None:
      self.save()
    self.h5File.name="runexamples_CompareResultFile_"+str(self.id)+"_"+filename

# delete all files referenced in CompareResultFile when a CompareResultFile object is deleted
def compareResultFileDeleteHandler(sender, **kwargs):
  crf=kwargs["instance"]
  if crf.h5File:
    crf.h5File.delete(False)
django.db.models.signals.pre_delete.connect(compareResultFileDeleteHandler, sender=CompareResultFile)

class CompareResultManager(django.db.models.Manager):
  def filterFailed(self):
    return self.filter(~Q(result=CompareResult.Result.PASSED))

class CompareResult(django.db.models.Model):
  class Result(django.db.models.IntegerChoices):
    PASSED = 0
    FAILED = 1
    FILENOTINCUR = 2
    FILENOTINREF = 3
    DATASETNOTINCUR = 4
    DATASETNOTINREF = 5
    LABELNOTINCUR = 6
    LABELNOTINREF = 7
    LABELDIFFER = 8
    LABELMISSING = 9

  objects=CompareResultManager()

  id=django.db.models.AutoField(primary_key=True)
  compareResultFile=django.db.models.ForeignKey(CompareResultFile, on_delete=django.db.models.CASCADE, related_name='results', to_field="uuid")
  dataset=AL(django.db.models.CharField(max_length=200), L.inline, L.list, L.search)
  label=AL(django.db.models.CharField(max_length=100), L.inline, L.list, L.search)
  result=django.db.models.IntegerField(choices=Result.choices)

  def getCurrent(self):
    if self.compareResultFile.example.run.build_run:
      return CompareResult.objects.filter(
           compareResultFile__example__run__buildType=self.compareResultFile.example.run.buildType,
           compareResultFile__example__exampleName=self.compareResultFile.example.exampleName,
           compareResultFile__h5Filename=self.compareResultFile.h5Filename,
           compareResultFile__example__run__build_run__fmatvecBranch=self.compareResultFile.example.run.build_run.fmatvecBranch,
           compareResultFile__example__run__build_run__hdf5serieBranch=self.compareResultFile.example.run.build_run.hdf5serieBranch,
           compareResultFile__example__run__build_run__openmbvBranch=self.compareResultFile.example.run.build_run.openmbvBranch,
           compareResultFile__example__run__build_run__mbsimBranch=self.compareResultFile.example.run.build_run.mbsimBranch,
           dataset=self.dataset,
           label=self.label).\
         order_by("-compareResultFile__example__run__startTime").first()
    else:
      return CompareResult.objects.filter(
           compareResultFile__example__run__buildType=self.compareResultFile.example.run.buildType,
           compareResultFile__example__exampleName=self.compareResultFile.example.exampleName,
           compareResultFile__h5Filename=self.compareResultFile.h5Filename,
           dataset=self.dataset,
           label=self.label).\
         order_by("-compareResultFile__example__run__startTime").first()
  def getNext(self):
    if self.compareResultFile.example.run.build_run:
      ret=CompareResult.objects.filter(
           compareResultFile__example__run__buildType=self.compareResultFile.example.run.buildType,
           compareResultFile__example__run__startTime__gt=self.compareResultFile.example.run.startTime,
           compareResultFile__example__exampleName=self.compareResultFile.example.exampleName,
           compareResultFile__h5Filename=self.compareResultFile.h5Filename,
           compareResultFile__example__run__build_run__fmatvecBranch=self.compareResultFile.example.run.build_run.fmatvecBranch,
           compareResultFile__example__run__build_run__hdf5serieBranch=self.compareResultFile.example.run.build_run.hdf5serieBranch,
           compareResultFile__example__run__build_run__openmbvBranch=self.compareResultFile.example.run.build_run.openmbvBranch,
           compareResultFile__example__run__build_run__mbsimBranch=self.compareResultFile.example.run.build_run.mbsimBranch,
           dataset=self.dataset,
           label=self.label).\
         order_by("compareResultFile__example__run__startTime").first()
    else:
      ret=CompareResult.objects.filter(
           compareResultFile__example__run__buildType=self.compareResultFile.example.run.buildType,
           compareResultFile__example__run__startTime__gt=self.compareResultFile.example.run.startTime,
           compareResultFile__example__exampleName=self.compareResultFile.example.exampleName,
           compareResultFile__h5Filename=self.compareResultFile.h5Filename,
           dataset=self.dataset,
           label=self.label).\
         order_by("compareResultFile__example__run__startTime").first()
    if ret is None:
      return self
    return ret
  def getPrevious(self):
    if self.compareResultFile.example.run.build_run:
      ret=CompareResult.objects.filter(
           compareResultFile__example__run__buildType=self.compareResultFile.example.run.buildType,
           compareResultFile__example__run__startTime__lt=self.compareResultFile.example.run.startTime,
           compareResultFile__example__exampleName=self.compareResultFile.example.exampleName,
           compareResultFile__h5Filename=self.compareResultFile.h5Filename,
           compareResultFile__example__run__build_run__fmatvecBranch=self.compareResultFile.example.run.build_run.fmatvecBranch,
           compareResultFile__example__run__build_run__hdf5serieBranch=self.compareResultFile.example.run.build_run.hdf5serieBranch,
           compareResultFile__example__run__build_run__openmbvBranch=self.compareResultFile.example.run.build_run.openmbvBranch,
           compareResultFile__example__run__build_run__mbsimBranch=self.compareResultFile.example.run.build_run.mbsimBranch,
           dataset=self.dataset,
           label=self.label).\
         order_by("-compareResultFile__example__run__startTime").first()
    else:
      ret=CompareResult.objects.filter(
           compareResultFile__example__run__buildType=self.compareResultFile.example.run.buildType,
           compareResultFile__example__run__startTime__lt=self.compareResultFile.example.run.startTime,
           compareResultFile__example__exampleName=self.compareResultFile.example.exampleName,
           compareResultFile__h5Filename=self.compareResultFile.h5Filename,
           dataset=self.dataset,
           label=self.label).\
         order_by("-compareResultFile__example__run__startTime").first()
    if ret is None:
      return self
    return ret
