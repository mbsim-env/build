import django
import builds.models
import django.contrib.contenttypes.models
import django.contrib.contenttypes.fields
import re
import uuid

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
      (django.db.models.Q(coverageOK__isnull=False)   & django.db.models.Q(coverageOK=False)) |
      django.db.models.Q(examplesFailed__gt=0)
    ).distinct()

class Run(django.db.models.Model):
  objects=RunManager()

  id=django.db.models.AutoField(primary_key=True)
  build_run=django.db.models.ForeignKey(builds.models.Run, null=True, blank=True, on_delete=django.db.models.SET_NULL, related_name="examples")
  buildType=django.db.models.CharField(max_length=50)
  command=django.db.models.TextField()
  startTime=django.db.models.DateTimeField()
  endTime=django.db.models.DateTimeField(null=True, blank=True)
  # examples = related ForeignKey
  examplesFailed=django.db.models.PositiveIntegerField(default=0) # just a cached value for performance of filterFailed
  coverageOK=django.db.models.BooleanField(null=True, blank=True)
  coverageRate=django.db.models.FloatField(null=True, blank=True)
  coverageOutput=django.db.models.TextField(blank=True)
  fmatvecLcov=django.db.models.TextField(blank=True)
  hdf5serieLcov=django.db.models.TextField(blank=True)
  openmbvLcov=django.db.models.TextField(blank=True)
  mbsimLcov=django.db.models.TextField(blank=True)

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
    return self.filter(django.db.models.Q(willFail=False) & (
      (django.db.models.Q(runResult__isnull=False)          & django.db.models.Q(runResult__in=[Example.RunResult.FAILED, Example.RunResult.TIMEDOUT])) |
      (django.db.models.Q(guiTestHdf5serieOK__isnull=False) & django.db.models.Q(guiTestHdf5serieOK=Example.GUITestResult.FAILED)) |
      (django.db.models.Q(guiTestOpenmbvOK__isnull=False)   & django.db.models.Q(guiTestOpenmbvOK=Example.GUITestResult.FAILED)) |
      (django.db.models.Q(guiTestMbsimguiOK__isnull=False)  & django.db.models.Q(guiTestMbsimguiOK=Example.GUITestResult.FAILED)) |
      (django.db.models.Q(deprecatedNr__isnull=False)       & django.db.models.Q(deprecatedNr__gt=0)) |
      django.db.models.Q(resultsFailed__gt=0) |
      django.db.models.Q(xmlOutputsFailed__gt=0)
    )).distinct()

class Example(django.db.models.Model):
  class RunResult(django.db.models.IntegerChoices):
    PASSED = 0
    FAILED = 1
    TIMEDOUT = 2
  class GUITestResult(django.db.models.IntegerChoices):
    PASSED = 0
    FAILED = 1
    TIMEDOUT = 2

  objects=ExampleManager()

  id=django.db.models.AutoField(primary_key=True)
  run=django.db.models.ForeignKey(Run, on_delete=django.db.models.CASCADE, related_name='examples')
  exampleName=django.db.models.CharField(max_length=200)
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
    id=Example.objects.filter(run__buildType=self.run.buildType,
                              exampleName=self.exampleName).\
       aggregate(django.db.models.Max('id'))["id__max"]
    return self if id is None else Example.objects.get(id=id)
  def getNext(self):
    id=Example.objects.filter(run__buildType=self.run.buildType,
                              run__id__gt=self.run.id,
                              exampleName=self.exampleName).\
       aggregate(django.db.models.Min('id'))["id__min"]
    return self if id is None else Example.objects.get(id=id)
  def getPrevious(self):
    id=Example.objects.filter(run__buildType=self.run.buildType,
                              run__id__lt=self.run.id,
                              exampleName=self.exampleName).\
       aggregate(django.db.models.Max('id'))["id__max"]
    return self if id is None else Example.objects.get(id=id)

class XMLOutputManager(django.db.models.Manager):
  # return a queryset with all failed xmloutput of the current queryset
  def filterFailed(self):
    return self.filter(resultOK=False)

class XMLOutput(django.db.models.Model):
  objects=XMLOutputManager()

  id=django.db.models.AutoField(primary_key=True)
  example=django.db.models.ForeignKey(Example, on_delete=django.db.models.CASCADE, related_name='xmlOutputs')
  filename=django.db.models.CharField(max_length=200)
  resultOK=django.db.models.BooleanField()
  resultOutput=django.db.models.TextField()

class ExampleStatic(django.db.models.Model):
  exampleName=django.db.models.CharField(max_length=200, primary_key=True)
  refTime=django.db.models.DurationField(null=True, blank=True)
  update=django.db.models.BooleanField(default=False)
  # references = related ForeignKey

class ExampleStaticReference(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  exampleStatic=django.db.models.ForeignKey(ExampleStatic, on_delete=django.db.models.CASCADE, related_name='references')
  h5File=django.db.models.FileField(null=True, blank=True, max_length=200)
  @property
  def h5FileName(self):
    if self.h5File is None: return None
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
  if esr.h5File is not None:
    esr.h5File.delete(False)
django.db.models.signals.pre_delete.connect(exampleStaticReferenceDeleteHandler, sender=ExampleStaticReference)

class Valgrind(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  uuid=django.db.models.UUIDField(unique=True, default=uuid.uuid4, editable=False) # used for ForeignKey to enable bulk_create
  programType=django.db.models.CharField(max_length=50)
  programCmd=django.db.models.TextField()
  valgrindCmd=django.db.models.TextField()
  example=django.db.models.ForeignKey(Example, on_delete=django.db.models.CASCADE, related_name="valgrinds")
  # errors = related ForeignKey

class ValgrindError(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  uuid=django.db.models.UUIDField(unique=True, default=uuid.uuid4, editable=False) # used for ForeignKey to enable bulk_create

  valgrind=django.db.models.ForeignKey(Valgrind, on_delete=django.db.models.CASCADE, related_name="errors", to_field="uuid")
  kind=django.db.models.CharField(max_length=100)
  # whatsAndStacks = related ForeignKey
  suppressionRawText=django.db.models.TextField()

class ValgrindWhatAndStack(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  uuid=django.db.models.UUIDField(unique=True, default=uuid.uuid4, editable=False) # used for ForeignKey to enable bulk_create
  valgrindError=django.db.models.ForeignKey(ValgrindError, on_delete=django.db.models.CASCADE, related_name="whatsAndStacks", to_field="uuid")
  nr=django.db.models.PositiveSmallIntegerField() # defines the order of the "what" (and stack) entries
  what=django.db.models.CharField(max_length=200)
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
  dir=django.db.models.CharField(max_length=250)
  file=django.db.models.CharField(max_length=100)
  line=django.db.models.PositiveIntegerField(null=True, blank=True)
  class Meta:
    constraints=[
      django.db.models.UniqueConstraint(fields=['whatAndStack', 'nr'], name="unique_orderPerStack"),
    ]

class CompareResultFile(django.db.models.Model):
  id=django.db.models.AutoField(primary_key=True)
  uuid=django.db.models.UUIDField(unique=True, default=uuid.uuid4, editable=False) # used for ForeignKey to enable bulk_create
  example=django.db.models.ForeignKey(Example, on_delete=django.db.models.CASCADE, related_name='resultFiles')
  # results = related ForeignKey
  h5Filename=django.db.models.CharField(max_length=100) # must be consistent with h5FileName if set
  h5File=django.db.models.FileField(null=True, blank=True, max_length=200)
  @property
  def h5FileName(self):
    if self.h5File is None: return None
    fn=re.sub("^runexamples_CompareResultFile_[0-9]+_", "", self.h5File.name)
    if fn!=self.h5Filename:
      raise RuntimeError("Filename missmatch in CompareResultFile")
    return fn
  @h5FileName.setter
  def h5FileName(self, filename):
    if filename!=self.h5Filename:
      raise RuntimeError("Filename missmatch in CompareResultFile")
    if self.id is None:
      self.save()
    self.h5File.name="runexamples_CompareResultFile_"+str(self.id)+"_"+filename

# delete all files referenced in CompareResultFile when a CompareResultFile object is deleted
def compareResultFileDeleteHandler(sender, **kwargs):
  crf=kwargs["instance"]
  if crf.h5File is not None:
    crf.h5File.delete(False)
django.db.models.signals.pre_delete.connect(compareResultFileDeleteHandler, sender=CompareResultFile)

class CompareResultManager(django.db.models.Manager):
  def filterFailed(self):
    return self.filter(~django.db.models.Q(result=CompareResult.Result.PASSED))

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
  dataset=django.db.models.CharField(max_length=200)
  label=django.db.models.CharField(max_length=100)
  result=django.db.models.IntegerField(choices=Result.choices)

  def getCurrent(self):
    id=CompareResult.objects.filter(compareResultFile__example__run__buildType=self.compareResultFile.example.run.buildType,
                                    compareResultFile__example__exampleName=self.compareResultFile.example.exampleName,
                                    compareResultFile__h5Filename=self.compareResultFile.h5Filename,
                                    dataset=self.dataset,
                                    label=self.label).\
       aggregate(django.db.models.Max('id'))["id__max"]
    return self if id is None else CompareResult.objects.get(id=id)
  def getNext(self):
    id=CompareResult.objects.filter(compareResultFile__example__run__buildType=self.compareResultFile.example.run.buildType,
                                    compareResultFile__example__run__id__gt=self.compareResultFile.example.run.id,
                                    compareResultFile__example__exampleName=self.compareResultFile.example.exampleName,
                                    compareResultFile__h5Filename=self.compareResultFile.h5Filename,
                                    dataset=self.dataset,
                                    label=self.label).\
       aggregate(django.db.models.Min('id'))["id__min"]
    return self if id is None else CompareResult.objects.get(id=id)
  def getPrevious(self):
    id=CompareResult.objects.filter(compareResultFile__example__run__buildType=self.compareResultFile.example.run.buildType,
                                    compareResultFile__example__run__id__lt=self.compareResultFile.example.run.id,
                                    compareResultFile__example__exampleName=self.compareResultFile.example.exampleName,
                                    compareResultFile__h5Filename=self.compareResultFile.h5Filename,
                                    dataset=self.dataset,
                                    label=self.label).\
       aggregate(django.db.models.Max('id'))["id__max"]
    return self if id is None else CompareResult.objects.get(id=id)
