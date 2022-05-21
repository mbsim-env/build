import django
import functools
import base

# admin model

class _MBSimEnvInlineModelAdmin(django.contrib.admin.TabularInline):
  show_change_link=True
  can_delete=False
  extra=0
  def __init__(self, model, admin_site, relatedModel, *args, **kwargs):
    self.model=relatedModel
    self.fields=[]
    for f in relatedModel._meta.get_fields():
      if hasattr(f, "mbsimenv_labels") and base.helper.FieldLabel.inline in f.mbsimenv_labels:
        self.fields.append(f.name)
    # pull in at least one field to avoid that all fields are used
    if len(self.fields)==0:
      self.fields=[relatedModel._meta.pk.name]
    self.readonly_fields=self.fields # all fields are read only
    super().__init__(model, admin_site, *args, **kwargs)
  def has_add_permission(self, request, obj):
    return False

class MBSimEnvModelAdmin(django.contrib.admin.ModelAdmin):
  def __init__(self, model, admin_site, *args, **kwargs):
    # mark all ForeignKey fields as raw_id_fields
    self.raw_id_fields=[]
    self.readonly_fields=[]
    self.list_display=[model._meta.pk.name]
    self.search_fields=[]
    for f in model._meta.get_fields():
      if isinstance(f, django.db.models.ForeignKey):
        self.raw_id_fields.append(f.name)
      if isinstance(f, django.db.models.UUIDField):
        self.readonly_fields.append(f.name)
      if hasattr(f, "mbsimenv_labels") and base.helper.FieldLabel.list in f.mbsimenv_labels:
        self.list_display.append(f.name)
      if hasattr(f, "mbsimenv_labels") and base.helper.FieldLabel.search in f.mbsimenv_labels:
        self.search_fields.append(f.name)
    super().__init__(model, admin_site, *args, **kwargs)
  def get_inlines(self, request, obj):
    # mark all related ManyToOneRel fields (reverse ForeignKey's) as inlines
    inlines=[]
    for f in self.model._meta.get_fields():
      if isinstance(f, django.db.models.fields.reverse_related.ManyToOneRel):
        inlines.append(functools.partial(_MBSimEnvInlineModelAdmin, relatedModel=f.related_model))
    return inlines



class SessionAdmin(django.contrib.admin.ModelAdmin):
  def decoded_session_data(self, obj):
    return obj.get_decoded()
  fields = ['session_key', 'decoded_session_data', 'expire_date']
  readonly_fields = ['decoded_session_data']
django.contrib.admin.site.register(django.contrib.sessions.models.Session, SessionAdmin)
