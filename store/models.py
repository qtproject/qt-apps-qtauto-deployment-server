#############################################################################
##
## Copyright (C) 2020 Luxoft Sweden AB
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

from django.db import models
from ordered_model.models import OrderedModel
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage

from utilities import packagePath, writeTempIcon, makeTagList

def category_file_name(instance, filename):
    # filename parameter is unused. See django documentation for details:
    # https://docs.djangoproject.com/en/1.11/ref/models/fields/#django.db.models.FileField.upload_to
    return settings.MEDIA_ROOT + "icons/category_" +  str(instance.id) + ".png"

class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name

class Category(OrderedModel):
    name = models.CharField(max_length = 200)
    icon = models.ImageField(upload_to = category_file_name, storage = OverwriteStorage())

    class Meta(OrderedModel.Meta):
        ordering = ('order',)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.id is None:
            # This is a django hack. When category icon is saved and then later accessed,
            # category_id is used as a unique icon identifier. When category is first created,
            # but not saved yet, category_id is None. So this hack first saves category without icon
            # and then saves the icon separately. This is done to prevent creation of category_None.png
            # file, when the icon is saved.
            saved_icon = self.icon
            self.icon = None
            super(Category, self).save(*args, **kwargs)
            self.icon = saved_icon
        super(Category, self).save(*args, **kwargs)

class Vendor(models.Model):
    user = models.ForeignKey(User, primary_key = False)
    name = models.CharField(max_length = 200)
    certificate = models.TextField(max_length = 8000)

    def __unicode__(self):
        return self.name


def content_file_name(instance, filename):
    return packagePath(instance.appid, instance.architecture, instance.tags)

class App(models.Model):
    appid = models.CharField(max_length = 200)
    name = models.CharField(max_length = 200)
    file = models.FileField(upload_to = content_file_name, storage = OverwriteStorage())
    vendor = models.ForeignKey(Vendor)
    category = models.ForeignKey(Category)
    briefDescription = models.TextField()
    description = models.TextField()
    dateAdded = models.DateField(auto_now_add = True)
    dateModified = models.DateField(auto_now = True)
    tags = models.TextField(blank=True)
    architecture = models.CharField(max_length=20, default='All')
    version = models.CharField(max_length=20, default='0.0.0')
    pkgformat = models.IntegerField()

    class Meta:
        """Makes the group of id and arch - a unique identifier"""
        unique_together = (('appid', 'architecture', 'tags'),)

    def __unicode__(self):
        return self.name + " [" + " ".join([self.appid, self.version, self.architecture, self.tags]) + "]"

    def save(self, *args, **kwargs):
        try:
            this = App.objects.get(appid=self.appid,architecture=self.architecture,tags=self.tags) #FIXME: This should be 'tags match, not exact same tags'
            if this.file != self.file:
                this.file.delete(save=False)
        except:
            pass
        super(App, self).save(*args, **kwargs)


def savePackageFile(pkgdata, pkgfile, category, vendor, description, shortdescription):
    appId = pkgdata['info']['id']
    name = pkgdata['storeName']
    architecture = pkgdata['architecture']
    pkgformat = pkgdata['packageFormat']['formatVersion']
    tags = makeTagList(pkgdata)
    success, error = writeTempIcon(appId, architecture, tags, pkgdata['icon'])
    if not success:
        raise Exception(error)

    exists = False
    app = None
    try:
        app = App.objects.get(appid__exact=appId, architecture__exact=architecture, tags__exact=tags)
        exists = True
    except App.DoesNotExist:
        pass

    if exists:
        app.appid = appId
        app.category = category
        app.vendor = vendor
        app.name = name
        app.tags = tags
        app.description = description
        app.briefDescription = shortdescription
        app.architecture = architecture
        app.pkgformat = pkgformat
        app.file.save(packagePath(appId, architecture, tags), pkgfile)
        app.save()
    else:
        app, _ = App.objects.get_or_create(name=name, tags=tags, vendor=vendor,
                                           category=category, appid=appId,
                                           briefDescription=shortdescription, description=description,
                                           pkgformat = pkgformat, architecture=architecture)
        app.file.save(packagePath(appId, architecture, tags), pkgfile)
        app.save()
