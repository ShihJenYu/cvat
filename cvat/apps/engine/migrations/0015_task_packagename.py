# Generated by Django 2.0.3 on 2019-01-11 10:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0014_auto_20190111_0318'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='packagename',
            field=models.CharField(default='', max_length=256),
        ),
    ]
