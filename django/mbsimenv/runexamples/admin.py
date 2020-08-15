import django
import runexamples

django.contrib.admin.site.register(runexamples.models.Run)
django.contrib.admin.site.register(runexamples.models.Example)
django.contrib.admin.site.register(runexamples.models.XMLOutput)
django.contrib.admin.site.register(runexamples.models.ExampleStatic)
django.contrib.admin.site.register(runexamples.models.ExampleStaticReference)
django.contrib.admin.site.register(runexamples.models.Valgrind)
django.contrib.admin.site.register(runexamples.models.ValgrindError)
django.contrib.admin.site.register(runexamples.models.ValgrindWhatAndStack)
django.contrib.admin.site.register(runexamples.models.ValgrindFrame)
django.contrib.admin.site.register(runexamples.models.CompareResultFile)
django.contrib.admin.site.register(runexamples.models.CompareResult)
