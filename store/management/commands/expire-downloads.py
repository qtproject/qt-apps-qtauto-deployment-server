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

import os
import time

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from store.utilities import downloadPath

class Command(BaseCommand):
    help = 'Expires all downloads that are older than APPSTORE_DOWNLOAD_EXPIRY minutes'

    def handle(self, *args, **options):
        self.stdout.write('Removing expired download packages')
        pkgPath = downloadPath()
        if not os.path.exists(pkgPath):
            os.makedirs(pkgPath)

        for pkg in os.listdir(pkgPath):
            t = os.path.getmtime(pkgPath + pkg)
            age = time.time() - t
            if age > (int(settings.APPSTORE_DOWNLOAD_EXPIRY) * 60):
               os.remove(pkgPath + pkg)
               self.stdout.write(' -> %s (age: %s seconds)' % (pkg, int(age)))

        self.stdout.write('Done')
