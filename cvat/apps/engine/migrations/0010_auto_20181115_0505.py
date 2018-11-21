# Generated by Django 2.0.3 on 2018-11-15 05:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0009_auto_20180917_1424'),
    ]

    operations = [
        migrations.CreateModel(
            name='FCWTrain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keyframe_count', models.PositiveIntegerField()),
                ('unchecked_count', models.PositiveIntegerField()),
                ('checked_count', models.PositiveIntegerField()),
                ('need_modify_count', models.PositiveIntegerField()),
                ('priority', models.PositiveIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='TaskFrameUserRecord',
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
                ('comment', models.CharField(max_length=2048)),
                ('userGet_date', models.DateTimeField(blank=True, null=True)),
                ('userSave_date', models.DateTimeField(blank=True, null=True)),
                ('userSubmit_date', models.DateTimeField(blank=True, null=True)),
                ('userModifyGet_date', models.DateTimeField(blank=True, null=True)),
                ('userModifySave_date', models.DateTimeField(blank=True, null=True)),
                ('userModifySubmit_date', models.DateTimeField(blank=True, null=True)),
                ('extraCategory', models.CharField(max_length=256)),
                ('defaultCategory', models.CharField(max_length=256)),
            ],
        ),
        migrations.AddField(
            model_name='task',
            name='category',
            field=models.CharField(default='', max_length=256),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='task',
            name='nickname',
            field=models.CharField(default='', max_length=256),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='attributespec',
            name='text',
            field=models.CharField(max_length=2084),
        ),
        migrations.AddField(
            model_name='taskframeuserrecord',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='engine.Task'),
        ),
        migrations.AddField(
            model_name='fcwtrain',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='engine.Task'),
        ),
    ]
