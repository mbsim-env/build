import django
import service

django.contrib.admin.site.register(service.models.CIBranches)
django.contrib.admin.site.register(service.models.Release)
django.contrib.admin.site.register(service.models.Manual)
django.contrib.admin.site.register(service.models.Info)
