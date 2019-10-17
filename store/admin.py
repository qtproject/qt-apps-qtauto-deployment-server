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

from django import forms
from django.contrib import admin
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy
from ordered_model.admin import OrderedModelAdmin
from django.core.files.uploadedfile import InMemoryUploadedFile

from store.models import *
from utilities import parseAndValidatePackageMetadata, writeTempIcon, makeTagList
import StringIO

class CategoryAdminForm(forms.ModelForm):
    class Meta:
        exclude = ["id", "rank"]

    def save(self, commit=False):
        m = super(CategoryAdminForm, self).save(commit=False)
        return m

    def clean(self):
        cleaned_data = super(CategoryAdminForm, self).clean()
        #Icon fixing (resize, turn monochrome, add alpha channel)
        if cleaned_data['icon']:
            if settings.ICON_DECOLOR:
                # make image monochrome + alpha channel, this is done to compensate for
                # how icons are treated in neptune3-ui
                im = Image.open(cleaned_data['icon'])
                grey, alpha = im.convert('LA').split()
                grey = ImageChops.invert(grey)
                im.putalpha(grey)
                im = im.convert('LA')
            else:
                # No conversion, icons are uploaded as-is, only scaling is used.
                im = Image.open(cleared_data['icon'])
            size = (settings.ICON_SIZE_X,settings.ICON_SIZE_Y,)
            im.thumbnail(size, Image.ANTIALIAS)
            imagefile = StringIO.StringIO()
            im.save(imagefile, format='png')
            imagefile.seek(0)
            cleaned_data['icon'] = InMemoryUploadedFile(imagefile, 'icon', "icon.png", 'image/png', imagefile.len, None)
        return cleaned_data

class CategoryAdmin(OrderedModelAdmin):
    form = CategoryAdminForm
    list_display = ('name', 'icon_image', 'move_up_down_links')
    ordering = ('order',)

    def save_model(self, request, obj, form, change):
        obj.save()

    def name(self, obj):
        # just to forbid sorting by name
        return obj.name
    name.short_description = ugettext_lazy('Item caption')

    def icon_image(self, obj):
        prefix = settings.URL_PREFIX
        image_request = prefix + "/category/icon?id=%s" % (obj.id)
        html = u'<img width=%s height=%s src="%s" />' % (settings.ICON_SIZE_X, settings.ICON_SIZE_Y, image_request)
        return html

    icon_image.allow_tags = True
    icon_image.short_description = ugettext_lazy('Category icon')


class AppAdminForm(forms.ModelForm):
    class Meta:
        exclude = ["appid", "name", "tags", "architecture", 'version']

    appId = ""
    name = ""

    def clean(self):
        cleaned_data = super(AppAdminForm, self).clean()
        file = cleaned_data.get('file')

        # validate package
        pkgdata = None
        try:
            pkgdata = parseAndValidatePackageMetadata(file)
        except Exception as error:
            raise forms.ValidationError(_('Validation error: %s' % str(error)))

        self.appId = pkgdata['info']['id']
        self.name = pkgdata['storeName']
        self.architecture = pkgdata['architecture']
        self.tags = makeTagList(pkgdata)

        # check if this really is an update
        if hasattr(self, 'instance') and self.instance.appid:
            if self.appId != self.instance.appid:
                raise forms.ValidationError(_('Validation error: an update cannot change the application id, tried to change from %s to %s' % (self.instance.appid, self.appId)))
            elif self.architecture != self.instance.architecture:
                raise forms.ValidationError(_('Validation error: an update cannot change the application architecture from %s to %s' % (self.instance.architecture, self.architecture)))
        else:
            try:
                if App.objects.get(appid__exact = self.appId, architecture__exact = self.architecture, tags__exact = self.tags):
                    raise forms.ValidationError(_('Validation error: another application with id %s , tags %s and architecture %s already exists' % (str(self.appId), str(self.tags), str(self.architecture))))
            except App.DoesNotExist:
                pass

        # write icon into file to serve statically
        success, error = writeTempIcon(self.appId, self.architecture, self.tags, pkgdata['icon'])
        if not success:
            raise forms.ValidationError(_(error))

        return cleaned_data

    def save(self, commit=False):
        m = super(AppAdminForm, self).save(commit)
        m.appid = self.appId
        m.name = self.name
        m.architecture = self.architecture

        m.file.seek(0)
        pkgdata = parseAndValidatePackageMetadata(m.file)
        m.tags = makeTagList(pkgdata)
        return m


class AppAdmin(admin.ModelAdmin):
    form = AppAdminForm
    list_display = ('name', 'appid', 'architecture', 'version', 'tags')

    def save_model(self, request, obj, form, change):
        obj.save()


admin.site.register(Category, CategoryAdmin)
admin.site.register(Vendor)
admin.site.register(App, AppAdmin)
