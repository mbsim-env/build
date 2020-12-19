import django
import runexamples
import base

django.contrib.admin.site.register(runexamples.models.Run, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.Example, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.XMLOutput, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.ExampleStatic, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.ExampleStaticReference, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.Valgrind, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.ValgrindError, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.ValgrindWhatAndStack, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.ValgrindFrame, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.CompareResultFile, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(runexamples.models.CompareResult, base.admin.MBSimEnvModelAdmin)
