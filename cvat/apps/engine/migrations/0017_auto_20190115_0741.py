# Generated by Django 2.0.3 on 2019-01-15 07:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0016_auto_20190114_0341'),
    ]

    operations = [
        migrations.AddField(
            model_name='apacorner',
            name='priority_out',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='fcwtest',
            name='priority_out',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='fcwtrain',
            name='priority_out',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
    ]