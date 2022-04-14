import django
import builds
import base
import runexamples

django.contrib.admin.site.register(builds.models.Run, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(builds.models.Tool, base.admin.MBSimEnvModelAdmin)
