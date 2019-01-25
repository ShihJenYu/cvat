
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

from django.urls import path
from . import views

urlpatterns = [
    path('', views.show_project_list),
    path('efficiencyTable', views.efficiencyTable),
    path('get/<str:project>/packagename', views.get_packagename),
    path('get/<str:user>/<str:project>/workSpace', views.get_workSpace),
    path('get/<str:project>/<str:package>/workSpaceUsers', views.get_workSpaceUsers),
    path('set/workSpaceUsers', views.set_workSpaceUsers),
]
