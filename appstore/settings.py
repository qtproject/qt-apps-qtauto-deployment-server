#############################################################################
##
## Copyright (C) 2019 Luxoft Sweden AB
## Copyright (C) 2018 Pelagicore AG
## Contact: https://www.qt.io/licensing/
##
## This file is part of the Neptune Deployment Server
##
## $QT_BEGIN_LICENSE:GPL-QTAS$
## Commercial License Usage
## Licensees holding valid commercial Qt Automotive Suite licenses may use
## this file in accordance with the commercial license agreement provided
## with the Software or, alternatively, in accordance with the terms
## contained in a written agreement between you and The Qt Company.  For
## licensing terms and conditions see https://www.qt.io/terms-conditions.
## For further information use the contact form at https://www.qt.io/contact-us.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 3 or (at your option) any later version
## approved by the KDE Free Qt Foundation. The licenses are as published by
## the Free Software Foundation and appearing in the file LICENSE.GPL3
## included in the packaging of this file. Please review the following
## information to ensure the GNU General Public License requirements will
## be met: https://www.gnu.org/licenses/gpl-3.0.html.
##
## $QT_END_LICENSE$
##
## SPDX-License-Identifier: GPL-3.0
##
#############################################################################

"""
Django settings for deployment server project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
import os

APPSTORE_MAINTENANCE       = False
APPSTORE_PLATFORM_ID       = os.getenv('APPSTORE_PLATFORM_ID', default = 'NEPTUNE3')
APPSTORE_PLATFORM_VERSION  = int(os.getenv('APPSTORE_PLATFORM_VERSION', default = '2'))
APPSTORE_DOWNLOAD_EXPIRY   = int(os.getenv('APPSTORE_DOWNLOAD_EXPIRY', default = '10'))     # in minutes
APPSTORE_BIND_TO_DEVICE_ID = os.getenv('APPSTORE_BIND_TO_DEVICE_ID', default = '1') == '1' # unique downloads for each device
APPSTORE_NO_SECURITY       = os.getenv('APPSTORE_NO_SECURITY', default = '1') == '1'        # ignore developer signatures and do not generate store signatures
APPSTORE_STORE_SIGN_PKCS12_CERTIFICATE = os.getenv('APPSTORE_STORE_SIGN_PKCS12_CERTIFICATE', default = 'certificates/store.p12')
APPSTORE_STORE_SIGN_PKCS12_PASSWORD    = os.getenv('APPSTORE_STORE_SIGN_PKCS12_PASSWORD', default = 'password')
APPSTORE_DEV_VERIFY_CA_CERTIFICATES    = os.getenv('APPSTORE_DEV_VERIFY_CA_CERTIFICATES', ','.join(['certificates/ca.crt', 'certificates/devca.crt'])).split(',')
APPSTORE_DATA_PATH         = os.getenv('APPSTORE_DATA_PATH', default = '')

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', default = '4%(o_1zuz@^kjcarw&!5ptvk&#9oa1-83*arn6jcm4idzy1#30')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': (
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages"
            ),
            'debug': True
        },
    },
]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ordered_model',
    'store',
)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'appstore.urls'

WSGI_APPLICATION = 'appstore.wsgi.application'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
if not APPSTORE_DATA_PATH:
  MEDIA_ROOT =  os.path.join(BASE_DIR, 'data/')
else:
  MEDIA_ROOT = APPSTORE_DATA_PATH

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MEDIA_ROOT, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = os.getenv('DJANGO_LANGUAGE_CODE', default = 'en-us')

TIME_ZONE = os.getenv('DJANGO_TIME_ZONE', default = 'Europe/Berlin')

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

URL_PREFIX = '' # Shouldn't start with '/' in case it is used

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# Icon size (icons are resized to this size on upload)
ICON_SIZE_X = 50
ICON_SIZE_Y = 50
# If the icon should be transformed to monochrome, with alpha channel, when uploaded or not
ICON_DECOLOR = False

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
