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
import shutil

from django.conf import settings
from django.db.models import Q, Count
from django.http import HttpResponse, HttpResponseForbidden, Http404, JsonResponse
from django.contrib import auth
from django.views.decorators.csrf import csrf_exempt
from authdecorators import logged_in_or_basicauth, is_staff_member

from models import App, Category, Vendor, savePackageFile
from utilities import parsePackageMetadata, parseAndValidatePackageMetadata, addSignatureToPackage
from utilities import packagePath, iconPath, downloadPath
from utilities import getRequestDictionary
from osandarch import normalizeArch
from tags import SoftwareTagList


def hello(request):
    status = 'ok'

    if settings.APPSTORE_MAINTENANCE:
        status = 'maintenance'
    elif getRequestDictionary(request).get("platform", "") != str(settings.APPSTORE_PLATFORM_ID):
        status = 'incompatible-platform'
    elif getRequestDictionary(request).get("version", "") != str(settings.APPSTORE_PLATFORM_VERSION):
        status = 'incompatible-version'

    for j in ("require_tag", "conflicts_tag",):
        if j in getRequestDictionary(request): #Tags are coma-separated,
            versionmap = SoftwareTagList()
            if not versionmap.parse(getRequestDictionary(request)[j]):
                status = 'malformed-tag'
                break
            request.session[j] = str(versionmap)
    if 'architecture' in getRequestDictionary(request):
        request.session['architecture'] = normalizeArch(getRequestDictionary(request)['architecture'])
    else:
        request.session['architecture'] = ''
    return JsonResponse({'status': status})


def login(request):
    status = 'ok'
    try:
        try:
            username = getRequestDictionary(request)["username"]
            password = getRequestDictionary(request)["password"]
        except KeyError:
            raise Exception('missing-credentials')

        user = auth.authenticate(username = username, password = password)
        if user is None:
            raise Exception('authentication-failed')

        if not user.is_active:
            raise Exception('account-disabled')

        auth.login(request, user)

    except Exception as error:
        status = str(error)

    return JsonResponse({'status': status})


def logout(request):
    status = 'ok'

    if not request.user.is_authenticated():
        status = 'failed'
    logout(request)

    return JsonResponse({'status': status})


@csrf_exempt
@logged_in_or_basicauth()
@is_staff_member()
def upload(request):
    status = 'ok'
    try:
        try:
            description = getRequestDictionary(request)["description"]
        except:
            raise Exception('no description')
        try:
            shortdescription = getRequestDictionary(request)["short-description"]
        except:
            raise Exception('no short description')
        try:
            category_name = getRequestDictionary(request)["category"]
        except:
            raise Exception('no category')
        try:
            vendor_name = getRequestDictionary(request)["vendor"]
        except:
            raise Exception('no vendor')

        if request.method == 'POST' and request.FILES['package']:
            myfile = request.FILES['package']
            category = Category.objects.all().filter(name__exact=category_name)
            vendor = Vendor.objects.all().filter(name__exact=vendor_name)
            if len(category) == 0:
                raise Exception('Non-existing category')
            if len(vendor) == 0:
                raise Exception('Non-existing vendor')

            try:
                pkgdata = parseAndValidatePackageMetadata(myfile)
            except:
                raise Exception('Package validation failed')

            myfile.seek(0)
            try:
                savePackageFile(pkgdata, myfile, category[0], vendor[0], description, shortdescription)
            except Exception as error:
                raise Exception(error)
        else:
            raise Exception('no package to upload')

    except Exception as error:
        status = str(error)
    return JsonResponse({'status': status})


def appList(request):
    apps = App.objects.all()
    if 'filter' in getRequestDictionary(request):
        apps = apps.filter(name__contains = getRequestDictionary(request)['filter'])
    if 'category_id' in getRequestDictionary(request):
        catId = getRequestDictionary(request)['category_id']
        if catId != -1: # All metacategory
            apps = apps.filter(category__exact = catId)

    #Tag filtering
    #"require_tag", "conflicts_tag"
    # Tags are combined by logical AND (for require) and logical OR for conflicts
    if 'require_tag' in request.session:
        require_tags = SoftwareTagList()
        require_tags.parse(request.session['require_tag'])
        for i in require_tags.make_regex():
            apps = apps.filter(Q(tags__regex = i))
    if 'conflicts_tag' in request.session:
        conflict_tags = SoftwareTagList()
        conflict_tags.parse(request.session['conflicts_tag'])
        for i in conflict_tags.make_regex():
            apps = apps.filter(~Q(tags__regex=i))

    # Here goes the logic of listing packages when multiple architectures are available
    # in /hello request, the target architecture is stored in the session. By definition target machine can support
    # both "All" package architecture and it's native one.
    # So - here goes filtering by list of architectures
    archlist = ['All', ]
    if 'architecture' in request.session:
        archlist.append(request.session['architecture'])
    apps = apps.filter(architecture__in = archlist)

    # After filtering, there are potential duplicates in list. And we should prefer native applications to pure qml ones
    # due to speedups offered.
    # So - first applications are grouped by appid and numbers of same appids counted. In case where is more than one appid -
    # there are two variants of application: for 'All' architecture, and for the architecture supported by the target machine.
    # So, as native apps should be preferred
    duplicates = (
        apps.values('appid').order_by().annotate(count_id=Count('id')).filter(count_id__gt=1)
    )
    # Here we go over duplicates list and filter out 'All' architecture apps.
    for duplicate in duplicates:
        apps = apps.filter(~Q(appid__exact = duplicate['appid'], architecture__exact = 'All')) # if there is native - 'All' architecture apps are excluded

    appList = list(apps.values('appid', 'name', 'vendor__name', 'briefDescription', 'category', 'tags', 'architecture', 'version').order_by('appid','architecture'))

    for app in appList:
        app['id'] = app['appid']
        app['category_id'] = app['category']
        app['category'] = Category.objects.all().filter(id__exact = app['category_id'])[0].name
        app['vendor'] = app['vendor__name']
        if app['tags'] != "":
            app['tags'] = app['tags'].split(',')
        else:
            app['tags'] = []
        del app['vendor__name']
        del app['appid']

    # this is not valid JSON, since we are returning a list!
    return JsonResponse(appList, safe = False)


def appDescription(request):
    archlist = ['All', ]
    if 'architecture' in request.session:
        archlist.append(request.session['architecture'])
    appId = getRequestDictionary(request)['id']
    try:
        app = App.objects.get(appid__exact = appId, architecture__in = archlist).order_by('architecture')
        app = app.last()
        return HttpResponse(app.description)
    except:
        raise Http404('no such application: %s' % appId)


def appIcon(request):
    archlist = ['All', ]
    if 'architecture' in request.session:
        archlist.append(request.session['architecture'])
    appId = getRequestDictionary(request)['id']
    try:
        app = App.objects.filter(appid__exact = appId, architecture__in = archlist).order_by('architecture')
        app = app.last()
        with open(iconPath(app.appid,app.architecture), 'rb') as iconPng:
            response = HttpResponse(content_type = 'image/png')
            response.write(iconPng.read())
            return response
    except:
        raise Http404('no such application: %s' % appId)


def appPurchase(request):
    if not request.user.is_authenticated():
        return HttpResponseForbidden('no login')
    archlist = ['All', ]
    if 'architecture' in request.session:
        archlist.append(request.session['architecture'])
    try:
        deviceId = str(getRequestDictionary(request).get("device_id", ""))
        if settings.APPSTORE_BIND_TO_DEVICE_ID:
            if not deviceId:
                return JsonResponse({'status': 'failed', 'error': 'device_id required'})
        else:
            deviceId = ''

        app = App.objects.filter(appid__exact = getRequestDictionary(request)['id'], architecture__in=archlist).order_by('architecture')
        app = app.last()
        fromFilePath = packagePath(app.appid, app.architecture)

        # we should not use obvious names here, but just hash the string.
        # this would be a nightmare to debug though and this is a development server :)
        toFile = str(app.appid) + '_' + str(request.user.id) + '_' + str(app.architecture) + '_' + str(deviceId) + '.appkg'
        toPath = downloadPath()
        if not os.path.exists(toPath):
            os.makedirs(toPath)

        if not settings.APPSTORE_NO_SECURITY:
            with open(fromFilePath, 'rb') as package:
                pkgdata = parsePackageMetadata(package)
                addSignatureToPackage(fromFilePath, toPath + toFile, pkgdata['rawDigest'], deviceId)
        else:
            shutil.copyfile(fromFilePath, toPath + toFile)

        if settings.URL_PREFIX != '':
            downloadUri = '/' + settings.URL_PREFIX + '/app/download/' + toFile
        else:
            downloadUri = '/app/download/' + toFile

        return JsonResponse({'status': 'ok',
                             'url': request.build_absolute_uri(downloadUri),
                             'expiresIn': int(settings.APPSTORE_DOWNLOAD_EXPIRY) * 60})

        # a cronjob runing "manage.py expiredownloads" every settings.APPSTORE_DOWNLOAD_EXPIRY/2
        # minutes will take care of removing these temporary download files.
    except Exception as error:
        return JsonResponse({ 'status': 'failed', 'error': str(error)})


def appDownload(request, path):
    try:
        response = HttpResponse(content_type = 'application/octetstream')
        with open(downloadPath() + path, 'rb') as pkg:
            response.write(pkg.read())
            response['Content-Length'] = pkg.tell()
        return response
    except:
        raise Http404


def categoryList(request):
    # this is not valid JSON, since we are returning a list!
    allmeta = [{'id': -1, 'name': 'All'}, ] #All metacategory
    categoryobject = Category.objects.all().order_by('rank').values('id', 'name')
    categoryobject=allmeta + list(categoryobject)
    return JsonResponse(categoryobject, safe = False)


def categoryIcon(request):
    response = HttpResponse(content_type = 'image/png')
    categoryId = getRequestDictionary(request)['id']

    # there are no category icons (yet), so we just return the icon of the first app in this category
    try:
        app = App.objects.filter(category__exact = categoryId).order_by('-dateModified')[0] #FIXME - the category icon is unimplemented
        with open(iconPath(app.appid,app.architecture), 'rb') as iconPng:
            response.write(iconPng.read())
    except:
        emptyPng = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00%\xdbV\xca\x00\x00\x00\x03PLTE\x00\x00\x00\xa7z=\xda\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\nIDAT\x08\xd7c`\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82'
        response.write(emptyPng)

    return response
