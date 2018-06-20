#############################################################################
##
## Copyright (C) 2016 Pelagicore AG
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
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage

from utilities import packagePath


class Category(models.Model):
    name = models.CharField(max_length = 200)
    rank = models.SmallIntegerField(unique = True, db_index = True)

    def __unicode__(self):
        return self.name

    def is_first(self):
        """
        Returns ``True`` if item is the first one in the menu.
        """
        return Category.objects.filter(rank__lt = self.rank).count() == 0

    def is_last(self):
        """
        Returns ``True`` if item is the last one in the menu.
        """
        return Category.objects.filter(rank__gt = self.rank).count() == 0

    def increase_rank(self):
        """
        Changes position of this item with the next item in the
        menu. Does nothing if this item is the last one.
        """
        try:
            next_item = Category.objects.filter(rank__gt = self.rank)[0]
        except IndexError:
            pass
        else:
            self.swap_ranks(next_item)

    def decrease_rank(self):
        """
        Changes position of this item with the previous item in the
        menu. Does nothing if this item is the first one.
        """
        try:
            list = Category.objects.filter(rank__lt = self.rank).reverse()
            prev_item = list[len(list) - 1]
        except IndexError:
            pass
        else:
            self.swap_ranks(prev_item)

    def swap_ranks(self, other):
        """
        Swap positions with ``other`` menu item.
        """
        maxrank = 5000
        prev_rank, self.rank = self.rank, maxrank
        self.save()
        self.rank, other.rank = other.rank, prev_rank
        other.save()
        self.save()

class Vendor(models.Model):
    user = models.ForeignKey(User, primary_key = True)
    name = models.CharField(max_length = 200)
    certificate = models.TextField(max_length = 8000)

    def __unicode__(self):
        return self.name


class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name):
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name

def content_file_name(instance, filename):
    return packagePath(instance.id)

class App(models.Model):
    id = models.CharField(max_length = 200, primary_key=True)
    name = models.CharField(max_length = 200)
    file = models.FileField(upload_to = content_file_name, storage = OverwriteStorage())
    vendor = models.ForeignKey(Vendor)
    category = models.ForeignKey(Category)
    briefDescription = models.TextField()
    description = models.TextField()
    dateAdded = models.DateField(auto_now_add = True)
    dateModified = models.DateField(auto_now = True)

    def __unicode__(self):
        return self.name + " [" + self.id + "]"

    def save(self, *args, **kwargs):
        try:
            this = App.objects.get(id=self.id)
            if this.file != self.file:
                this.file.delete(save=False)
        except:
            pass
        super(App, self).save(*args, **kwargs)
