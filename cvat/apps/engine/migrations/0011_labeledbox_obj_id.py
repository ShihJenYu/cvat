# Generated by Django 2.0.3 on 2018-12-14 04:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0010_auto_20181115_0505'),
    ]

    operations = [
        migrations.AddField(
            model_name='labeledbox',
            name='obj_id',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='labeledpolygon',
            name='obj_id',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='labeledpolyline',
            name='obj_id',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='labeledpoints',
            name='obj_id',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
    ]
