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

import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from store.utilities import parseAndValidatePackageMetadata, addSignatureToPackage

class Command(BaseCommand):
    help = 'Adds a store signature to the package'

    def handle(self, *args, **options):
        if 2 > len(args) > 3:
            raise CommandError('Usage: manage.py store-sign-package <source package> <destination-package> [device id]')

        sourcePackage = args[0]
        destinationPackage = args[1]
        deviceId = args[2] if len(args) == 3 else ''

        try:
            self.stdout.write('Parsing package %s' % sourcePackage)
            packageFile = open(sourcePackage, 'rb')
            pkgdata = parseAndValidatePackageMetadata(packageFile)
            self.stdout.write('  -> passed validation (internal name: %s)\n' % pkgdata['storeName'])

            self.stdout.write('Adding signature to package %s' % destinationPackage)
            addSignatureToPackage(sourcePackage, destinationPackage, pkgdata['rawDigest'], deviceId)
            self.stdout.write('  -> finished')

        except Exception as error:
            self.stdout.write('  -> failed: %s\n' % str(error))
            raise
