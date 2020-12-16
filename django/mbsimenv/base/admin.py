import django

# admin model
class MBSimEnvModelAdmin(django.contrib.admin.ModelAdmin):
  raw_id_fields = ()
  def __init__(self, model, admin_site, *args, **kwargs):
    self.raw_id_fields = tuple( f.name for f in model._meta.get_fields() if isinstance(f, django.db.models.ForeignKey) )
    super().__init__(model, admin_site, *args, **kwargs)
