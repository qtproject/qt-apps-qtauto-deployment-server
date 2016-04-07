#############################################################################
##
## Copyright (C) 2016 Pelagicore AG
## Contact: https://www.qt.io/licensing/
##
## This file is part of the Neptune AppStore Server
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

import sys

from django.core.management.base import BaseCommand, CommandError

from store.utilities import parseAndValidatePackageMetadata

class Command(BaseCommand):
    help = 'Checks if packages are valid for store upload'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Usage: manage.py verify-upload-package <package>')

        try:
            self.stdout.write('Parsing package %s' % args[0])
            packageFile = open(args[0], 'rb')
            pkgdata = parseAndValidatePackageMetadata(packageFile)

            self.stdout.write('  -> passed validation (internal name: %s)\n' % pkgdata['storeName'])

        except Exception as error:
            self.stdout.write('  -> failed: %s\n' % str(error))
