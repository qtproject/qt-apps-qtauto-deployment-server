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

import argparse

from django.core.management.base import BaseCommand, CommandError

from store.utilities import parseAndValidatePackageMetadata, addSignatureToPackage

class Command(BaseCommand):
    help = 'Adds a store signature to the package'

    def add_arguments(self, parser):
        parser.add_argument('source-package',
                            metavar='sourcepackage',
                            type=argparse.FileType('rb'),
                            nargs=1,
                            help='package file to sign')
        parser.add_argument('destination-package',
                            metavar='destinationpackage',
                            type=str,
                            nargs=1,
                            help='signed package file destination')
        parser.add_argument('device ID',
                            metavar='deviceID',
                            type=str,
                            nargs='?',
                            default="",
                            help='device ID')

    def handle(self, *args, **options):
        if not options["source-package"]:
            raise CommandError('Usage: manage.py store-sign-package <source package>\
 <destination-package> [device id]')

        source_package = options["source-package"]
        destination_package = options["destination-package"][0]
        device_id = options["device ID"]

        try:
            self.stdout.write('Parsing package %s' % source_package[0].name)
            package_file = source_package[0]
            pkgdata = parseAndValidatePackageMetadata(package_file)
            self.stdout.write('  -> passed validation (internal name: %s)\n' % pkgdata['storeName'])

            self.stdout.write('Adding signature to package %s' % destination_package)
            addSignatureToPackage(source_package[0].name, destination_package, pkgdata['rawDigest'],
                                  device_id, pkgdata['packageFormat']['formatVersion'])
            self.stdout.write('  -> finished')

        except Exception as error:
            self.stdout.write('  -> failed: %s\n' % str(error))
            raise
