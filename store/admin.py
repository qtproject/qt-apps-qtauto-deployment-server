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

import io
from PIL import Image, ImageChops

from django import forms
from django.contrib import admin
from django.core.files.uploadedfile import InMemoryUploadedFile
from ordered_model.admin import OrderedModelAdmin
from django.utils.safestring import mark_safe

from store.models import *
from store.utilities import parseAndValidatePackageMetadata, writeTempIcon, makeTagList

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
                grey, _ = im.convert('LA').split()
                grey = ImageChops.invert(grey)
                im.putalpha(grey)
                im = im.convert('LA')
            else:
                # No conversion, icons are uploaded as-is, only scaling is used.
                im = Image.open(cleaned_data['icon'])
            size = (settings.ICON_SIZE_X, settings.ICON_SIZE_Y)
            im.thumbnail(size, Image.ANTIALIAS)
            imagefile = io.BytesIO()
            im.save(imagefile, format='png')
            length = imagefile.tell()
            imagefile.seek(0)
            cleaned_data['icon'] = InMemoryUploadedFile(imagefile, 'icon', "icon.png", 'image/png', length, None)
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
    name.short_description = u'Item caption'

    def icon_image(self, obj):
        prefix = settings.URL_PREFIX
        image_request = prefix + "/category/icon?id=%s" % (obj.id)
        html = '<img width=%s height=%s src="%s" />' % (settings.ICON_SIZE_X, settings.ICON_SIZE_Y, image_request)
        return mark_safe(html)

    icon_image.short_description = u'Category icon'


class AppAdminForm(forms.ModelForm):
    class Meta:
        exclude = ["appid", "name", "tags", "tags_hash", "architecture", 'version', 'pkgformat']

    appId = ""
    name = ""

    def clean(self):
        cleaned_data = super(AppAdminForm, self).clean()
        package_file = cleaned_data.get('file')

        # validate package
        pkgdata = None
        try:
            pkgdata = parseAndValidatePackageMetadata(package_file)
        except Exception as error:
            raise forms.ValidationError('Validation error: %s' % str(error))

        self.appId = pkgdata['info']['id']
        self.name = pkgdata['storeName']
        self.architecture = pkgdata['architecture']
        require_tags, conflict_tags, self.tags_hash = makeTagList(pkgdata)

        # check if this really is an update
        if hasattr(self, 'instance') and self.instance.appid:
            if self.appId != self.instance.appid:
                raise forms.ValidationError('Validation error: an update cannot change the '
                                            'application id, tried to change from %s to %s' %
                                            (self.instance.appid, self.appId))
            elif self.architecture != self.instance.architecture:
                raise forms.ValidationError('Validation error: an update cannot change the '
                                            'application architecture from %s to %s' %
                                            (self.instance.architecture, self.architecture))
        else:
            try:
                if App.objects.get(appid__exact=self.appId, architecture__exact=self.architecture, tags_hash__exact=self.tags_hash):
                    raise forms.ValidationError('Validation error: another application with id'
                                                ' %s , tags %s and architecture %s already '
                                                'exists' % (str(self.appId), str(self.tags_hash),
                                                            str(self.architecture)))
            except App.DoesNotExist:
                pass

        # write icon into file to serve statically
        success, error = writeTempIcon(self.appId, self.architecture, self.tags_hash, pkgdata['icon'])
        if not success:
            raise forms.ValidationError(error)

        return cleaned_data

    def save(self, commit=False):
        m = super(AppAdminForm, self).save(commit)
        m.appid = self.appId
        m.name = self.name
        m.architecture = self.architecture

        m.file.seek(0)
        pkgdata = parseAndValidatePackageMetadata(m.file)
        tags, conflict_tags, m.tags_hash = makeTagList(pkgdata)

        # FIXME - add tags?
        taglist = populateTagList(tags.list(),conflict_tags.list())

        # FIXME: clean tags beforehand
        m.pkgformat = pkgdata['packageFormat']['formatVersion']
        m.save()

        for i in taglist:
            # attach tags to app
            m.tags.add(i)

        return m


class AppAdmin(admin.ModelAdmin):
    form = AppAdminForm
    list_display = ('name', 'appid', 'architecture', 'version', 'pkgformat', 'tags_hash')

    def save_model(self, request, obj, form, change):
        obj.save()

class TagAdmin(admin.ModelAdmin):
    list_display = ('negative', 'name', 'version')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.save()

admin.site.register(Category, CategoryAdmin)
admin.site.register(Vendor)
admin.site.register(Tag, TagAdmin)
admin.site.register(App, AppAdmin)
