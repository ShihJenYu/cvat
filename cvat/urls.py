
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

"""CVAT URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import url  
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cvat.apps.others.urls')),
    path('dashboard/', include('cvat.apps.dashboard.urls')),
    path('django-rq/', include('django_rq.urls')),
    path('auth/', include('cvat.apps.authentication.urls')),
    path('documentation/', include('cvat.apps.documentation.urls')),
    path('logs/', include('cvat.apps.log_proxy.urls')),

    # projects
    path('fcw_testing/', include('cvat.apps.engine.urls')),
    path('otofcw_testing/', include('cvat.apps.engine.urls')),
    path('fcw_training/', include('cvat.apps.engine.urls')),
    path('otofcw_training/', include('cvat.apps.engine.urls')),
    path('apacorenr/', include('cvat.apps.engine.urls')),
    path('otoapacorenr/', include('cvat.apps.engine.urls')),
]

if 'yes' == os.environ.get('TF_ANNOTATION', 'no'):
    urlpatterns += [path('tf_annotation/', include('cvat.apps.tf_annotation.urls'))]
