#############################################################################
##
## Copyright (C) 2016 Pelagicore AG
## Contact: http://www.qt.io/ or http://www.pelagicore.com/
##
## This file is part of the Neptune AppStore Server
##
## $QT_BEGIN_LICENSE:GPL3-PELAGICORE$
## Commercial License Usage
## Licensees holding valid commercial Neptune AppStore Server
## licenses may use this file in accordance with the commercial license
## agreement provided with the Software or, alternatively, in accordance
## with the terms contained in a written agreement between you and
## Pelagicore. For licensing terms and conditions, contact us at:
## http://www.pelagicore.com.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 3 as published by the Free Software
## Foundation and appearing in the file LICENSE.GPLv3 included in the
## packaging of this file. Please review the following information to
## ensure the GNU General Public License version 3 requirements will be
## met: http://www.gnu.org/licenses/gpl-3.0.html.
##
## $QT_END_LICENSE$
##
## SPDX-License-Identifier: GPL-3.0
##
#############################################################################

from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'appstore.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'^hello$',             'store.api.hello'),
    url(r'^login$',             'store.api.login'),
    url(r'^logout$',            'store.api.logout'),
    url(r'^app/list$',          'store.api.appList'),
    url(r'^app/icon',           'store.api.appIcon'),
    url(r'^app/description',    'store.api.appDescription'),
    url(r'^app/purchase',       'store.api.appPurchase'),
    url(r'^app/download/(.*)$', 'store.api.appDownload'),
    url(r'^category/list$',     'store.api.categoryList'),
    url(r'^category/icon$',     'store.api.categoryIcon'),
)
