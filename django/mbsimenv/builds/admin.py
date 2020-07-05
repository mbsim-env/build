import django
import builds

django.contrib.admin.site.register(builds.models.Run)
django.contrib.admin.site.register(builds.models.Tool)
