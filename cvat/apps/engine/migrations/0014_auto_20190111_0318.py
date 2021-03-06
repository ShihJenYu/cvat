# Generated by Django 2.0.3 on 2019-01-11 03:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0013_auto_20181225_0633'),
    ]

    operations = [
        migrations.CreateModel(
            name='APACorner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keyframe_count', models.PositiveIntegerField()),
                ('unchecked_count', models.PositiveIntegerField()),
                ('checked_count', models.PositiveIntegerField()),
                ('need_modify_count', models.PositiveIntegerField()),
                ('priority', models.PositiveIntegerField()),
                ('user', models.CharField(max_length=150)),
                ('checker', models.CharField(max_length=150)),
                ('current', models.BooleanField(default=False)),
                ('user_submit', models.BooleanField(default=False)),
                ('need_modify', models.BooleanField(default=False)),
                ('checked', models.BooleanField(default=False)),
                ('userGet_date', models.DateTimeField(blank=True, null=True)),
                ('userSave_date', models.DateTimeField(blank=True, null=True)),
                ('userSubmit_date', models.DateTimeField(blank=True, null=True)),
                ('userModifyGet_date', models.DateTimeField(blank=True, null=True)),
                ('userModifySave_date', models.DateTimeField(blank=True, null=True)),
                ('userModifySubmit_date', models.DateTimeField(blank=True, null=True)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='engine.Task')),
            ],
        ),
        migrations.CreateModel(
            name='APACorner_FrameUserRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frame', models.PositiveIntegerField()),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('checker', models.CharField(max_length=150)),
                ('current', models.BooleanField(default=False)),
                ('user_submit', models.BooleanField(default=False)),
                ('need_modify', models.BooleanField(default=False)),
                ('checked', models.BooleanField(default=False)),
                ('comment', models.CharField(max_length=2048)),
                ('extraCategory', models.CharField(max_length=256)),
                ('defaultCategory', models.CharField(max_length=256)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='engine.Task')),
            ],
        ),
        migrations.CreateModel(
            name='FrameName',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frame', models.PositiveIntegerField()),
                ('name', models.CharField(default='', max_length=256)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='engine.Task')),
            ],
        ),
        migrations.AlterField(
            model_name='labeledboxattributeval',
            name='value',
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name='labeledpointsattributeval',
            name='value',
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name='labeledpolygonattributeval',
            name='value',
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name='labeledpolylineattributeval',
            name='value',
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name='objectpathattributeval',
            name='value',
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name='trackedboxattributeval',
            name='value',
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name='trackedpointsattributeval',
            name='value',
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name='trackedpolygonattributeval',
            name='value',
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name='trackedpolylineattributeval',
            name='value',
            field=models.CharField(max_length=128),
        ),
    ]
