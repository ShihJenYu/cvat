
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dispatch_request),
    #path('', views.dispatch_request2),
    #path('create/task', views.create_task),
    path('get/task/<str:tid>/frame/<int:frame>', views.get_frame),
    #path('check/task/<int:tid>', views.check_task),
    #path('delete/task/<int:tid>', views.delete_task),
    #path('update/task/<int:tid>', views.update_task),
    path('get/job/<int:jid>', views.get_job),
    #path('get/task/<int:tid>', views.get_task),
    #path('dump/annotation/task/<int:tid>', views.dump_annotation),
    # path('check/annotation/task/<int:tid>', views.check_annotation),
    # path('download/annotation/task/<int:tid>', views.download_annotation),
    path('save/annotation/job/<int:jid>', views.save_annotation_for_job),
    #path('save/annotation/task/<int:tid>', views.save_annotation_for_task),
    path('get/annotation/job/<int:jid>', views.get_annotation),
    path('get/username', views.get_username),
    path('save/exception/<int:jid>', views.catch_client_exception),
    # add by jeff
    path('set/current/job/<int:jid>', views.set_user_currnet),
    path('get/current/job/<int:jid>', views.get_user_currnet),
    path('get/isAdmin', views.get_isAdmin),
    path('get/task/<str:tid>/keyframes', views.get_keyFrames),
    path('set/task/<str:tid>/frame/<int:frame>/isKeyFrame/<int:flag>', views.set_frame_isKeyFrame),
    path('get/task/<str:tid>/frame/<int:frame>/isKeyFrame', views.get_frame_isKeyFrame),
    path('get/task/<str:tid>/frame/<int:frame>/keyframeStage', views.get_keyFrame_stage),
    path('get/annotation/job/<int:jid>/frame/<int:frame>', views.get_annotation_frame),

    path('set/task/<str:tid>/frame/<int:frame>/isComplete/<int:flag>', views.set_frame_isComplete),
    path('set/task/<str:tid>/frame/<int:frame>/isRedo/<int:flag>', views.set_frame_isRedo),
    path('set/task/<str:tid>/frame/<int:frame>/redoComment/<str:comment>', views.set_frame_redoComment),

    # path('set/tasks/priority', views.set_tasks_priority),
    # path('set/task/<int:tid>/nickname/<str:nickname>', views.set_task_nickname),

    path('get/fcw/job', views.get_FCW_Job),
    path('get/fcw/job/name/<int:jid>', views.get_FCW_Job_Name),
    # add by Eric
    path('update_keyframe', views.update_keyframe),
]
