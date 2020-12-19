import django
import service
import base

django.contrib.admin.site.register(service.models.CIBranches, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(service.models.CIQueue, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(service.models.DailyBranches, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(service.models.Release, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(service.models.Manual, base.admin.MBSimEnvModelAdmin)
django.contrib.admin.site.register(service.models.Info, base.admin.MBSimEnvModelAdmin)
