
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
    path('get/job/<int:jid>', views.get_job),
    path('save/annotation/job/<int:jid>', views.save_annotation_for_job),
    path('get/annotation/job/<int:jid>', views.get_annotation),
    path('get/username', views.get_username),
    path('save/exception/<int:jid>', views.catch_client_exception),

    # add by jeff
    path('get/isAdmin', views.get_isAdmin),

    path('save/currentJob', views.save_currentJob),
    path('get/currentJob', views.get_currentJob),
    path('set/currentJob', views.set_currentJob),
    
    path('get/task/<str:tid>/keyframes', views.get_keyFrames),
    path('set/task/<str:tid>/frame/<int:frame>/isKeyFrame/<int:flag>', views.set_frame_isKeyFrame),
    path('get/task/<str:tid>/frame/<int:frame>/keyframeStage', views.get_keyFrame_stage),
    path('get/annotation/job/<int:jid>/frame/<int:frame>', views.get_annotation_frame),

    path('set/task/<str:tid>/frame/<int:frame>/isComplete/<int:flag>', views.set_frame_isComplete),
    path('set/task/<str:tid>/frame/<int:frame>/isRedo/<int:flag>', views.set_frame_isRedo),
    path('set/task/<str:tid>/frame/<int:frame>/redoComment/<str:comment>', views.set_frame_redoComment),

    path('set/task/<str:tid>/isRedo/<int:flag>', views.set_job_isRedo),

    # path('get/fcw/job', views.get_FCW_Job),
    # path('get/fcw/job/name/<int:jid>', views.get_FCW_Job_Name),

    # add by Eric
    path('set/task/<int:tid>/catogory/<str:catogory>', views.set_Video_Catogory),

]
