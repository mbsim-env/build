# Generated by Django 3.0.1 on 2020-08-15 10:05

from django.db import migrations, models
import django.db.models.deletion
import uuid

# NOTE!!!!!
# this migration will delete all existing CompareResult datasets!!!!
def deleteCompareResults(apps, schema_editor):
    cmpRes = apps.get_model("runexamples", "CompareResult")
    cmpRes.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('runexamples', '0004_filterfailed'),
    ]

    operations = [
        migrations.RunPython(deleteCompareResults),
        migrations.RemoveField(
            model_name='compareresult',
            name='example',
        ),
        migrations.RemoveField(
            model_name='compareresult',
            name='h5File',
        ),
        migrations.RemoveField(
            model_name='compareresult',
            name='h5Filename',
        ),
        migrations.CreateModel(
            name='CompareResultFile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('h5Filename', models.CharField(max_length=100)),
                ('h5File', models.FileField(blank=True, max_length=200, null=True, upload_to='')),
                ('example', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resultFiles', to='runexamples.Example')),
            ],
        ),
        migrations.AddField(
            model_name='compareresult',
            name='compareResultFile',
            field=models.ForeignKey(default=uuid.uuid4, on_delete=django.db.models.deletion.CASCADE, related_name='results', to='runexamples.CompareResultFile', to_field='uuid'),
            preserve_default=False,
        ),
    ]
