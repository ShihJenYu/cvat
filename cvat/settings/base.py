
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

"""
Django settings for CVAT project.

Generated by 'django-admin startproject' using Django 2.0.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import sys
from pathlib import Path

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = str(Path(__file__).parents[2])

ALLOWED_HOSTS = ['localhost', '192.168.2.71']
INTERNAL_IPS = ['127.0.0.1']

try:
    sys.path.append(BASE_DIR)
    from keys.secret_key import SECRET_KEY
except ImportError:
    from django.utils.crypto import get_random_string
    with open(os.path.join(BASE_DIR, 'keys', 'secret_key.py'), 'w') as f:
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        f.write("SECRET_KEY = '{}'\n".format(get_random_string(50, chars)))
    from keys.secret_key import SECRET_KEY

# Application definition
JS_3RDPARTY = {}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cvat.apps.engine',
    'cvat.apps.dashboard',
    'cvat.apps.authentication',
    'cvat.apps.documentation',
    'django_rq',
    'compressor',
    'cacheops',
    'sendfile',
    'dj_pagination',
]

if 'yes' == os.environ.get('TF_ANNOTATION', 'no'):
    INSTALLED_APPS += ['cvat.apps.tf_annotation']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dj_pagination.middleware.PaginationMiddleware',
]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

ROOT_URLCONF = 'cvat.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cvat.wsgi.application'

# Django-RQ
# https://github.com/rq/django-rq

RQ_QUEUES = {
    'default': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
        'DEFAULT_TIMEOUT': '1h'
    },
    'low': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
        'DEFAULT_TIMEOUT': '24h'
    }
}

RQ_SHOW_ADMIN_LINK = True
RQ_EXCEPTION_HANDLERS = ['cvat.apps.engine.views.rq_handler']


# JavaScript and CSS compression
# https://django-compressor.readthedocs.io

COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.rCSSMinFilter'
]
COMPRESS_JS_FILTERS = []  # No compression for js files (template literals were compressed bad)

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Cache DB access (e.g. for engine.task.get_frame)
# https://github.com/Suor/django-cacheops
CACHEOPS_REDIS = {
    'host': 'localhost', # redis-server is on same machine
    'port': 6379,        # default redis port
    'db': 1,             # SELECT non-default redis database
}

CACHEOPS = {
    # Automatically cache any Task.objects.get() calls for 15 minutes
    # This also includes .first() and .last() calls.
    'engine.task': {'ops': 'get', 'timeout': 60*15},
}

CACHEOPS_DEGRADE_ON_FAILURE = True

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
            'filename': os.path.join(BASE_DIR, 'logs', 'cvat.log'),
            'formatter': 'standard',
            'maxBytes': 1024*1024*50, # 50 MB
            'backupCount': 5,
        }
    },
    'loggers': {
        'cvat': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
        }
    },
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
os.makedirs(STATIC_ROOT, exist_ok=True)
DATA_ROOT = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_ROOT, exist_ok=True)
SHARE_ROOT = os.path.join(BASE_DIR, 'share')
os.makedirs(SHARE_ROOT, exist_ok=True)

DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = None   # this django check disabled
LOCAL_LOAD_MAX_FILES_COUNT = 500
LOCAL_LOAD_MAX_FILES_SIZE = 512 * 1024 * 1024  # 512 MB
