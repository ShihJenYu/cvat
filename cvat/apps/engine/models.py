
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

from django.db import models
from django.conf import settings

from django.contrib.auth.models import User

import shlex
import csv
from io import StringIO
import re
import os


class Task(models.Model):
    name = models.CharField(max_length=256)
    nickname = models.CharField(max_length=256)
    category = models.CharField(max_length=256)
    packagename = models.CharField(max_length=1024,default="")
    size = models.PositiveIntegerField()
    path = models.CharField(max_length=256)
    mode = models.CharField(max_length=32)
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    bug_tracker = models.CharField(max_length=2000, default="")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, default="annotate")
    overlap = models.PositiveIntegerField(default=0)
    z_order = models.BooleanField(default=False)
    flipped = models.BooleanField(default=False)

    # Extend default permission model
    class Meta:
        permissions = (
            ("view_task", "Can see available tasks"),
            ("view_annotation", "Can see annotation for the task"),
            ("change_annotation", "Can modify annotation for the task"),
        )

    def get_upload_dirname(self):
        return os.path.join(self.path, ".upload")

    def get_data_dirname(self):
        return os.path.join(self.path, "data")

    def get_dump_path(self):
        name = re.sub(r'[\\/*?:"<>|]', '_', self.name)
        return os.path.join(self.path, "{}.dump".format(name))

    def get_log_path(self):
        return os.path.join(self.path, "task.log")

    def get_client_log_path(self):
        return os.path.join(self.path, "client.log")

    def get_image_meta_cache_path(self):
        return os.path.join(self.path, "image_meta.cache")

    def set_task_dirname(self, path):
        self.path = path
        self.save(update_fields=['path'])

    def get_task_dirname(self):
        return self.path

    def __str__(self):
        return self.name

class Segment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    start_frame = models.IntegerField()
    stop_frame = models.IntegerField()

class Job(models.Model):
    segment = models.ForeignKey(Segment, on_delete=models.CASCADE)
    annotator = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    # TODO: add sub-issue number for the task

class Label(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

def parse_attribute(text):
    match = re.match(r'^([~@])(\w+)=(\w+):(.+)?$', text)
    prefix = match.group(1)
    type = match.group(2)
    name = match.group(3)
    if match.group(4):
        values = list(csv.reader(StringIO(match.group(4)), quotechar="'"))[0]
    else:
        values = []

    return {'prefix':prefix, 'type':type, 'name':name, 'values':values}

class AttributeSpec(models.Model):
    label = models.ForeignKey(Label, on_delete=models.CASCADE)
    text  = models.CharField(max_length=2084)

    def get_attribute(self):
        return parse_attribute(self.text)

    def is_mutable(self):
        attr = self.get_attribute()
        return attr['prefix'] == '~'

    def get_type(self):
        attr = self.get_attribute()
        return attr['type']

    def get_name(self):
        attr = self.get_attribute()
        return attr['name']

    def get_default_value(self):
        attr = self.get_attribute()
        return attr['values'][0]

    def get_values(self):
        attr = self.get_attribute()
        return attr['values']


    def __str__(self):
        return self.get_attribute()['name']

class AttributeVal(models.Model):
    # TODO: add a validator here to be sure that it corresponds to self.label
    id = models.BigAutoField(primary_key=True)
    spec = models.ForeignKey(AttributeSpec, on_delete=models.CASCADE)
    value = models.CharField(max_length=128)
    class Meta:
        abstract = True

class Annotation(models.Model):
    job   = models.ForeignKey(Job, on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)
    frame = models.PositiveIntegerField()
    group_id = models.PositiveIntegerField(default=0)
    class Meta:
        abstract = True

class Shape(models.Model):
    occluded = models.BooleanField(default=False)
    z_order = models.IntegerField(default=0)
    class Meta:
        abstract = True

class BoundingBox(Shape):
    id = models.BigAutoField(primary_key=True)
    xtl = models.FloatField()
    ytl = models.FloatField()
    xbr = models.FloatField()
    ybr = models.FloatField()
    class Meta:
        abstract = True

class PolyShape(Shape):
    id = models.BigAutoField(primary_key=True)
    points = models.TextField()
    class Meta:
        abstract = True

class LabeledBox(Annotation, BoundingBox):
    # add by eric
    obj_id = models.PositiveIntegerField()
    grouping = models.CharField(max_length=32, default='')
    pass

class LabeledBoxAttributeVal(AttributeVal):
    box = models.ForeignKey(LabeledBox, on_delete=models.CASCADE)

class LabeledPolygon(Annotation, PolyShape):
    # add by jeff
    obj_id = models.PositiveIntegerField()
    grouping = models.CharField(max_length=32, default='')
    pass

class LabeledPolygonAttributeVal(AttributeVal):
    polygon = models.ForeignKey(LabeledPolygon, on_delete=models.CASCADE)

class LabeledPolyline(Annotation, PolyShape):
    # add by jeff
    obj_id = models.PositiveIntegerField()
    grouping = models.CharField(max_length=32, default='')
    pass

class LabeledPolylineAttributeVal(AttributeVal):
    polyline = models.ForeignKey(LabeledPolyline, on_delete=models.CASCADE)

class LabeledPoints(Annotation, PolyShape):
    # add by jeff
    obj_id = models.PositiveIntegerField()
    grouping = models.CharField(max_length=32, default='')
    pass

class LabeledPointsAttributeVal(AttributeVal):
    points = models.ForeignKey(LabeledPoints, on_delete=models.CASCADE)

class ObjectPath(Annotation):
    id = models.BigAutoField(primary_key=True)
    shapes = models.CharField(max_length=10, default='boxes')

class ObjectPathAttributeVal(AttributeVal):
    track = models.ForeignKey(ObjectPath, on_delete=models.CASCADE)

class TrackedObject(models.Model):
    track = models.ForeignKey(ObjectPath, on_delete=models.CASCADE)
    frame = models.PositiveIntegerField()
    outside = models.BooleanField(default=False)
    class Meta:
        abstract = True

class TrackedBox(TrackedObject, BoundingBox):
    pass

class TrackedBoxAttributeVal(AttributeVal):
    box = models.ForeignKey(TrackedBox, on_delete=models.CASCADE)

class TrackedPolygon(TrackedObject, PolyShape):
    pass

class TrackedPolygonAttributeVal(AttributeVal):
    polygon = models.ForeignKey(TrackedPolygon, on_delete=models.CASCADE)

class TrackedPolyline(TrackedObject, PolyShape):
    pass

class TrackedPolylineAttributeVal(AttributeVal):
    polyline = models.ForeignKey(TrackedPolyline, on_delete=models.CASCADE)

class TrackedPoints(TrackedObject, PolyShape):
    pass

class TrackedPointsAttributeVal(AttributeVal):
    points = models.ForeignKey(TrackedPoints, on_delete=models.CASCADE)

# add by jeff
class TaskFrameUserRecord(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    frame = models.PositiveIntegerField()
    user = models.CharField(max_length=150)
    create_date = models.DateTimeField(auto_now_add=True)
    checker = models.CharField(max_length=150)
    current = models.BooleanField(default=False)
    user_submit = models.BooleanField(default=False)
    need_modify = models.BooleanField(default=False)
    checked = models.BooleanField(default=False)
    need_modify_date = models.DateTimeField(null=True, blank=True)
    checked_date = models.DateTimeField(null=True, blank=True)
    comment = models.CharField(max_length=2048)
    userGet_date = models.DateTimeField(null=True, blank=True)
    userSave_date = models.DateTimeField(null=True, blank=True)
    userSubmit_date = models.DateTimeField(null=True, blank=True)
    userModifyGet_date = models.DateTimeField(null=True, blank=True)
    userModifySave_date = models.DateTimeField(null=True, blank=True)
    userModifySubmit_date = models.DateTimeField(null=True, blank=True)
    extraCategory = models.CharField(max_length=256)
    defaultCategory = models.CharField(max_length=256)
    packagename = models.CharField(max_length=1024,default="")

class FCWTrain(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    keyframe_count = models.PositiveIntegerField()
    unchecked_count = models.PositiveIntegerField()
    checked_count = models.PositiveIntegerField()
    need_modify_count = models.PositiveIntegerField()
    priority = models.PositiveIntegerField()
    priority_out = models.PositiveIntegerField()

class FCWTest_FrameUserRecord(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    frame = models.PositiveIntegerField()
    create_date = models.DateTimeField(auto_now_add=True)
    checker = models.CharField(max_length=150)
    current = models.BooleanField(default=False)
    user_submit = models.BooleanField(default=False)
    need_modify = models.BooleanField(default=False)
    checked = models.BooleanField(default=False)
    comment = models.CharField(max_length=2048)
    extraCategory = models.CharField(max_length=256)
    defaultCategory = models.CharField(max_length=256)
    packagename = models.CharField(max_length=1024,default="")
    
class FCWTest(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    keyframe_count = models.PositiveIntegerField()
    unchecked_count = models.PositiveIntegerField()
    checked_count = models.PositiveIntegerField()
    need_modify_count = models.PositiveIntegerField()
    priority = models.PositiveIntegerField()
    priority_out = models.PositiveIntegerField()
    user = models.CharField(max_length=150)
    checker = models.CharField(max_length=150)
    current = models.BooleanField(default=False)
    user_submit = models.BooleanField(default=False)
    need_modify = models.BooleanField(default=False)
    checked = models.BooleanField(default=False)
    need_modify_date = models.DateTimeField(null=True, blank=True)
    checked_date = models.DateTimeField(null=True, blank=True)
    userGet_date = models.DateTimeField(null=True, blank=True)
    userSave_date = models.DateTimeField(null=True, blank=True)
    userSubmit_date = models.DateTimeField(null=True, blank=True)
    userModifyGet_date = models.DateTimeField(null=True, blank=True)
    userModifySave_date = models.DateTimeField(null=True, blank=True)
    userModifySubmit_date = models.DateTimeField(null=True, blank=True)


class APACorner_FrameUserRecord(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    frame = models.PositiveIntegerField()
    create_date = models.DateTimeField(auto_now_add=True)
    checker = models.CharField(max_length=150)
    current = models.BooleanField(default=False)
    user_submit = models.BooleanField(default=False)
    need_modify = models.BooleanField(default=False)
    checked = models.BooleanField(default=False)
    comment = models.CharField(max_length=2048)
    extraCategory = models.CharField(max_length=256)
    defaultCategory = models.CharField(max_length=256)
    packagename = models.CharField(max_length=1024,default="")
    
class APACorner(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    keyframe_count = models.PositiveIntegerField()
    unchecked_count = models.PositiveIntegerField()
    checked_count = models.PositiveIntegerField()
    need_modify_count = models.PositiveIntegerField()
    priority = models.PositiveIntegerField()
    priority_out = models.PositiveIntegerField()
    user = models.CharField(max_length=150)
    checker = models.CharField(max_length=150)
    current = models.BooleanField(default=False)
    user_submit = models.BooleanField(default=False)
    need_modify = models.BooleanField(default=False)
    checked = models.BooleanField(default=False)
    need_modify_date = models.DateTimeField(null=True, blank=True)
    checked_date = models.DateTimeField(null=True, blank=True)
    userGet_date = models.DateTimeField(null=True, blank=True)
    userSave_date = models.DateTimeField(null=True, blank=True)
    userSubmit_date = models.DateTimeField(null=True, blank=True)
    userModifyGet_date = models.DateTimeField(null=True, blank=True)
    userModifySave_date = models.DateTimeField(null=True, blank=True)
    userModifySubmit_date = models.DateTimeField(null=True, blank=True)

class FrameName(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    frame = models.PositiveIntegerField()
    name =  models.CharField(max_length=256, default="")