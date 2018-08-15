#############################################################################
##
## Copyright (C) 2018 Luxoft
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

from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from store.models import App, Category, Vendor
from store.utilities import parseAndValidatePackageMetadata, packagePath, makeTagList, writeTempIcon
from optparse import make_option


class Command(BaseCommand):
    help = 'Uploads a package to the deployment server. This can be used for batch uploading.'
    option_list = BaseCommand.option_list + (
        make_option('--vendor',
                    action='store',
                    type="string",
                    dest='vendor',
                    help='Vendor name'),
        make_option('--category',
                    action='store',
                    type="string",
                    dest='category',
                    help='Category name'),
        make_option('--description',
                    action='store',
                    type="string",
                    dest='description',
                    default="Empty description",
                    help='Short package description'),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError(
                'Usage: manage.py store-upload-package --vendor <vendor> --category <category> [--description <short description>] <package>')
        if (not options['vendor']) or (not options['category']):
            raise CommandError(
                'Usage: manage.py store-upload-package --vendor <vendor> --category <category> [--description <short description>] <package>')
        category = Category.objects.all().filter(name__exact=options['category'])
        vendor = Vendor.objects.all().filter(name__exact=options['vendor'])
        if len(category) == 0:
            raise CommandError('Non-existing category specified')
        if len(vendor) == 0:
            raise CommandError('Non-existing vendor specified')

        try:
            self.stdout.write('Parsing package %s' % args[0])
            packagefile = open(args[0], 'rb')
            pkgdata = parseAndValidatePackageMetadata(packagefile)
            self.stdout.write('  -> passed validation (internal name: %s)\n' % pkgdata['storeName'])
        except Exception as error:
            self.stdout.write('  -> failed: %s\n' % str(error))
            return 0

        packagefile.seek(0)
        appId = pkgdata['info']['id']
        name = pkgdata['storeName']
        architecture = pkgdata['architecture']
        description = options['description']
        tags = makeTagList(pkgdata)

        success, error = writeTempIcon(appId, architecture, pkgdata['icon'])
        if not success:
            raise CommandError(error)

        exists = False
        app = None
        try:
            app = App.objects.get(appid__exact=appId, architecture__exact= architecture)
            exists = True
        except App.DoesNotExist:
            pass

        if exists:
            app.appid = appId
            app.category = category[0]
            app.vendor = vendor[0]
            app.name = name
            app.tags = tags
            app.description = app.briefDescription = description
            app.architecture = architecture
            app.file.save(packagePath(appId, architecture), ContentFile(packagefile.read()))
            app.save()
        else:
            app, created = App.objects.get_or_create(name=name, tags=tags, vendor=vendor[0],
                                                     category=category[0], appid=appId,
                                                     briefDescription=description, description=description,
                                                     architecture=architecture)
            app.file.save(packagePath(appId, architecture), ContentFile(packagefile.read()))
            app.save()
