# Generated by Django 3.0 on 2024-04-09 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('runexamples', '0011_run_sourcedir'),
    ]

    operations = [
        migrations.AddField(
            model_name='compareresult',
            name='rtolminmax',
            field=models.FloatField(default=0),
        ),
    ]