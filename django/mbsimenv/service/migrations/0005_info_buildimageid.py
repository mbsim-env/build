# Generated by Django 3.0.1 on 2020-08-15 07:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0004_auto_20200719_1920'),
    ]

    operations = [
        migrations.AddField(
            model_name='info',
            name='buildImageID',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
    ]
