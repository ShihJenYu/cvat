
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

from django.urls import path
from . import views


from cvat.apps.engine import views as views2
urlpatterns = [
    path('get_share_nodes', views.JsTreeView),
    # add by jeff
    path('create/task', views2.create_task),
    path('check/task/<int:tid>', views2.check_task),
    path('delete/task/<int:tid>', views2.delete_task),
    path('update/task/<int:tid>', views2.update_task),
    path('save/annotation/task/<int:tid>', views2.save_annotation_for_task),
    path('get/task/<int:tid>', views2.get_task),
    path('check/annotation/task/<int:tid>', views2.check_annotation),
    path('download/annotation/task/<int:tid>', views2.download_annotation),
    path('dump/annotation/task/<int:tid>', views2.dump_annotation),
    path('set/tasks/priority', views2.set_tasks_priority),
    path('set/task/<int:tid>/nickname/<str:nickname>', views2.set_task_nickname),
    path('insert_images', views2.insert_images),
    path('upload_XML', views2.upload_Label),

    path('get/tasks/from/package', views.newDashboardView),
    path('get/tasks/from/search', views.searchDashboardView),
    path('set/package/priority', views.setPackagePriority),
    path('get/package/all/priority', views.getAllPackagePriority),

    # add by Eric
    path('upload_keyframe', views2.upload_keyframe),
    path('upload_CSV', views2.upload_CSV),

    # projects
    path('fcw_testing', views.DashboardView),
    path('otofcw_testing', views.DashboardView),
    path('fcw_training', views.DashboardView),
    path('otofcw_training', views.DashboardView),
    path('apacorner', views.DashboardView),
    path('otoapacorner', views.DashboardView),
    path('bsd_training', views.DashboardView),
    path('otobsd_training', views.DashboardView),
    path('dms_training', views.DashboardView),
    path('otodms_training', views.DashboardView),
]

