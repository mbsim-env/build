# Generated by Django 3.2.19 on 2024-12-22 12:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('runexamples', '0012_compareresult_rtolminmax'),
    ]

    operations = [
        migrations.AddField(
            model_name='valgrind',
            name='errorsErrors',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='valgrind',
            name='errorsWarnings',
            field=models.PositiveIntegerField(default=0),
        ),
    ]