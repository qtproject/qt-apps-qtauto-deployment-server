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

from django.conf.urls import include, url
from django.contrib import admin
from store import api as store_api
from appstore.settings import URL_PREFIX

base_urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),

    url(r'^hello$',             store_api.hello),
    url(r'^login$',             store_api.login),
    url(r'^logout$',            store_api.logout),
    url(r'^app/list$',          store_api.appList),
    url(r'^app/icons/(.*)$',    store_api.appIconNew),
    url(r'^app/icon',           store_api.appIcon),
    url(r'^app/description',    store_api.appDescription),
    url(r'^app/purchase',       store_api.appPurchase),
    url(r'^app/download/(.*)$', store_api.appDownload),
    url(r'^category/list$',     store_api.categoryList),
    url(r'^category/icon$',     store_api.categoryIcon),
    url(r'^upload$',            store_api.upload),
]


prefix = '^'
if URL_PREFIX != '':
    prefix = prefix + URL_PREFIX + '/'

urlpatterns = [
    url(prefix, include(base_urlpatterns)),
]

