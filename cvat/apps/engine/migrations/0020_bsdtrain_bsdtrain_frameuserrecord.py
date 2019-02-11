# Generated by Django 2.0.3 on 2019-02-11 07:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0019_userworkspace'),
    ]

    operations = [
        migrations.CreateModel(
            name='BSDTrain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keyframe_count', models.PositiveIntegerField()),
                ('unchecked_count', models.PositiveIntegerField()),
                ('checked_count', models.PositiveIntegerField()),
                ('need_modify_count', models.PositiveIntegerField()),
                ('priority', models.PositiveIntegerField()),
                ('priority_out', models.PositiveIntegerField()),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='engine.Task')),
            ],
        ),
        migrations.CreateModel(
            name='BSDTrain_FrameUserRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frame', models.PositiveIntegerField()),
                ('user', models.CharField(max_length=150)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('checker', models.CharField(max_length=150)),
                ('current', models.BooleanField(default=False)),
                ('user_submit', models.BooleanField(default=False)),
                ('need_modify', models.BooleanField(default=False)),
                ('checked', models.BooleanField(default=False)),
                ('need_modify_date', models.DateTimeField(blank=True, null=True)),
                ('checked_date', models.DateTimeField(blank=True, null=True)),
                ('comment', models.CharField(max_length=2048)),
                ('userGet_date', models.DateTimeField(blank=True, null=True)),
                ('userSave_date', models.DateTimeField(blank=True, null=True)),
                ('userSubmit_date', models.DateTimeField(blank=True, null=True)),
                ('userModifyGet_date', models.DateTimeField(blank=True, null=True)),
                ('userModifySave_date', models.DateTimeField(blank=True, null=True)),
                ('userModifySubmit_date', models.DateTimeField(blank=True, null=True)),
                ('extraCategory', models.CharField(max_length=256)),
                ('defaultCategory', models.CharField(max_length=256)),
                ('packagename', models.CharField(default='', max_length=1024)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='engine.Task')),
            ],
        ),
    ]