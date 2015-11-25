#############################################################################
##
## Copyright (C) 2015 Pelagicore AG
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

import os
import time

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from store.utilities import downloadPath

class Command(BaseCommand):
    help = 'Expires all downloads that are older than 10 minutes'

    def handle(self, *args, **options):
        self.stdout.write('Removing expired download packages')
        pkgPath = downloadPath()
        if not os.path.exists(pkgPath):
            os.makedirs(pkgPath)

        for pkg in os.listdir(pkgPath):
            t = os.path.getmtime(pkgPath + pkg)
            age = time.time() - t
            if age > (10 * 60):
               os.remove(pkgPath + pkg)
               self.stdout.write(' -> %s (age: %s seconds)' % (pkg, int(age)))

        self.stdout.write('Done')
