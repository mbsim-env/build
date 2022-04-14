# Generated by Django 3.0.1 on 2022-02-13 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('runexamples', '0008_run_executor'),
    ]

    operations = [
       migrations.AddField(
            model_name='examplestatic',
            name='queued',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='examplestatic',
            name='totalTimeNormal',
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='examplestatic',
            name='totalTimeValgrind',
            field=models.DurationField(blank=True, null=True),
        ),
    ]
