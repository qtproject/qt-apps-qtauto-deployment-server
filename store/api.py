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
import hashlib

from django.conf import settings
from django.db.models import Q, Count
from django.http import HttpResponse, HttpResponseForbidden, Http404, JsonResponse
from django.contrib import auth
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from store.authdecorators import logged_in_or_basicauth, is_staff_member

from store.models import App, Category, Vendor, savePackageFile
from store.utilities import parsePackageMetadata, parseAndValidatePackageMetadata, \
    addSignatureToPackage
from store.utilities import packagePath, iconPath, downloadPath
from store.utilities import getRequestDictionary
from store.osandarch import normalizeArch
from store.tags import SoftwareTagList


def hello(request):
    status = 'ok'
    dictionary = getRequestDictionary(request)
    try:
        version = int(dictionary.get("version", "-1"))
        if version > 256: #Sanity check against DoS attack (memory exhaustion)
            version = -1
    except:
        version = -1

    if settings.APPSTORE_MAINTENANCE:
        status = 'maintenance'
    elif dictionary.get("platform", "") != str(settings.APPSTORE_PLATFORM_ID):
        status = 'incompatible-platform'
    elif not ((version) > 0 and (version <= settings.APPSTORE_PLATFORM_VERSION)):
        status = 'incompatible-version'

    # Tag parsing
    temp_tags = []
    for j in ("require_tag", "tag"):
        if j in dictionary:
            temp_tags.append(dictionary[j])
    versionmap = SoftwareTagList()
    #Tags are coma-separated, - so join them
    if temp_tags:
        if not versionmap.parse(','.join(temp_tags)):
            status = 'malformed-tag'
    request.session["tag"] = str(versionmap)
    del temp_tags

    if 'architecture' in dictionary:
        arch = normalizeArch(dictionary['architecture'])
        if arch == "":
            status = 'incompatible-architecture'
        request.session['architecture'] = arch
    else:
        request.session['architecture'] = ''

    request.session['pkgversions'] = range(1, version + 1)
    return JsonResponse({'status': status})


def login(request):
    status = 'ok'
    try:
        try:
            username = getRequestDictionary(request)["username"]
            password = getRequestDictionary(request)["password"]
        except KeyError:
            raise Exception('missing-credentials')

        user = auth.authenticate(username=username, password=password)
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
            if not category:
                raise Exception('Non-existing category')
            if not vendor:
                raise Exception('Non-existing vendor')

            try:
                pkgdata = parseAndValidatePackageMetadata(myfile)
            except:
                raise Exception('Package validation failed')

            myfile.seek(0)
            try:
                package_metadata = {'category':category[0],
                                    'vendor':vendor[0],
                                    'description':description,
                                    'short_description':shortdescription}
                savePackageFile(pkgdata, myfile, package_metadata)
            except Exception as error:
                raise Exception(error)
        else:
            raise Exception('no package to upload')

    except Exception as error:
        status = str(error)
    return JsonResponse({'status': status})


def appList(request):
    apps = App.objects.all()
    dictionary = getRequestDictionary(request)
    if 'filter' in dictionary:
        apps = apps.filter(name__contains=dictionary['filter'])
    if 'category_id' in dictionary:
        catId = dictionary['category_id']
        if catId != -1: # All metacategory
            apps = apps.filter(category__exact=catId)

    # Here goes the logic of listing packages when multiple architectures are available
    # in /hello request, the target architecture is stored in the session. By definition
    # target machine can support both "All" package architecture and it's native one.
    # So - here goes filtering by list of architectures
    archlist = ['All', ]
    if 'architecture' in request.session:
        archlist.append(request.session['architecture'])

    versionlist = [1]
    if 'pkgversions' in request.session:
        versionlist = request.session['pkgversions']

    apps = apps.filter(architecture__in=archlist)
    apps = apps.filter(pkgformat__in=versionlist)

    #Tag filtering
    #There is no search by version distance yet - this must be fixed
    if 'tag' in request.session:
        tags = SoftwareTagList()
        tags.parse(request.session['tag'])
        apps_ids = [app.id for app in apps if app.is_tagmatching(tags.list())]
        apps = App.objects.filter(id__in=apps_ids)

    # After filtering, there are potential duplicates in list. And we should prefer native
    # applications to pure qml ones due to speedups offered.
    # At this point - filtering duplicates is disabled, because it will be implemented with
    # 'distance' between requested version and package version. Architecture will be also included
    # in this metric (as native apps should be preferred)

    selectedAppList = apps.values('id', 'appid', 'name', 'vendor__name', 'briefDescription',
                                       'category', 'architecture',
                                       'version', 'pkgformat', 'tags_hash').order_by('appid', 'architecture', 'tags_hash')

    appList = []
    for app in selectedAppList:
        app['purchaseId'] = app['id']
        app['id'] = app['appid']
        app['category_id'] = app['category']
        app['category'] = Category.objects.all().filter(id__exact=app['category_id'])[0].name
        app['vendor'] = app['vendor__name']
        app['tags'] = []
        tags = list(App.objects.filter(appid=app['appid'], architecture=app['architecture'], tags_hash=app['tags_hash'], tags__negative=False).values('tags__name', 'tags__version'))
        for i in tags:
            app['tags'].append(i['tags__name'] if not i['tags__version'] else ':'.join((i['tags__name'],i['tags__version'])))
        app['conflict_tags'] = []
        conflict_tags = list(App.objects.filter(appid=app['appid'], architecture=app['architecture'], tags_hash=app['tags_hash'], tags__negative=True).values('tags__name', 'tags__version'))
        for i in conflict_tags:
            app['conflict_tags'].append(i['tags__name'] if not i['tags__version'] else ':'.join((i['tags__name'],i['tags__version'])))

        toFile = '_'.join([app['appid'], app['architecture'], app['tags_hash']])
        if settings.URL_PREFIX != '':
            iconUri = '/' + settings.URL_PREFIX + '/app/icons/' + toFile
        else:
            iconUri = '/app/icons/' + toFile
        app['iconUrl'] = request.build_absolute_uri(iconUri)
        del app['vendor__name']
        del app['appid']
        del app['tags_hash']
        appList.append(app)

    # this is not valid JSON, since we are returning a list!
    return JsonResponse(appList, safe=False)


def appDescription(request):
    archlist = ['All', ]
    if 'architecture' in request.session:
        archlist.append(request.session['architecture'])
    versionlist = [1]
    if 'pkgversions' in request.session:
        versionlist = request.session['pkgversions']
    appId = getRequestDictionary(request)['id']
    try:
        app = App.objects.filter(appid__exact = appId, architecture__in = archlist).order_by('architecture','tags_hash')
        app = app.filter(pkgformat__in=versionlist)
        #Tag filtering
        #There is no search by version distance yet - this must be fixed
        if 'tag' in request.session:
            tags = SoftwareTagList()
            tags.parse(request.session['tag'])
            app_ids = [x.id for x in app if x.is_tagmatching(tags.list())]
            app = App.objects.filter(id__in=app_ids)
        app = app.last()
        return HttpResponse(app.description)
    except:
        raise Http404('no such application: %s' % appId)


def appIconNew(request, path):
    path=path.replace('/', '_').replace('\\', '_').replace(':', 'x3A').replace(',', 'x2C') + '.png'
    try:
        response = HttpResponse(content_type='image/png')
        with open(iconPath() + path, 'rb') as pkg:
            response.write(pkg.read())
            response['Content-Length'] = pkg.tell()
        return response
    except:
        raise Http404

def appIcon(request):
    archlist = ['All', ]
    dictionary = getRequestDictionary(request)
    if 'architecture' in dictionary:
        archlist.append(normalizeArch(dictionary['architecture']))
    elif 'architecture' in request.session:
        archlist.append(request.session['architecture'])
    versionlist = [1]
    if 'pkgversions' in request.session:
        versionlist = request.session['pkgversions']
    appId = dictionary['id']
    try:
        app = App.objects.filter(appid__exact = appId, architecture__in = archlist).order_by('architecture','tags_hash')
        app = app.filter(pkgformat__in=versionlist)
        #Tag filtering
        #There is no search by version distance yet - this must be fixed
        if 'tag' in request.session:
            tags = SoftwareTagList()
            tags.parse(request.session['tag'])
            app_ids = [x.id for x in app if x.is_tagmatching(tags.list())]
            app = App.objects.filter(id__in=app_ids)
        app = app.last()
        with open(iconPath(app.appid, app.architecture, app.tags_hash), 'rb') as iconPng:
            response = HttpResponse(content_type='image/png')
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
    versionlist = [1]
    if 'pkgversions' in request.session:
        versionlist = request.session['pkgversions']

    try:
        deviceId = str(getRequestDictionary(request).get("device_id", ""))
        if settings.APPSTORE_BIND_TO_DEVICE_ID:
            if not deviceId:
                return JsonResponse({'status': 'failed', 'error': 'device_id required'})
        else:
            deviceId = ''

        if 'id' in getRequestDictionary(request):
            app = App.objects.filter(appid__exact = getRequestDictionary(request)['id'], architecture__in=archlist).order_by('architecture','tags_hash')
        elif 'purchaseId' in getRequestDictionary(request):
            app = App.objects.filter(id__exact = getRequestDictionary(request)['purchaseId'], architecture__in=archlist).order_by('architecture','tags_hash')
        else:
            raise ValidationError('id or purchaseId parameter required')
        app = app.filter(pkgformat__in=versionlist)
        #Tag filtering
        #There is no search by version distance yet - this must be fixed
        if 'tag' in request.session:
            tags = SoftwareTagList()
            tags.parse(request.session['tag'])
            app_ids = [x.id for x in app if x.is_tagmatching(tags.list())]
            app = App.objects.filter(id__in=app_ids)

        app = app.last()
        fromFilePath = packagePath(app.appid, app.architecture, app.tags_hash)

        # we should not use obvious names here, but just hash the string.
        # this would be a nightmare to debug though and this is a development server :)
        toFile = '_'.join((str(app.appid), str(request.user.id), str(app.architecture),
                           str(app.tags_hash), str(deviceId)))
        if not settings.DEBUG:
            toFile = hashlib.sha256(toFile).hexdigest()
        toFile += '.appkg'
        toPath = downloadPath()
        if not os.path.exists(toPath):
            os.makedirs(toPath)

        if not settings.APPSTORE_NO_SECURITY:
            with open(fromFilePath, 'rb') as package:
                pkgdata = parsePackageMetadata(package)
                addSignatureToPackage(fromFilePath, toPath + toFile, pkgdata['rawDigest'], deviceId,
                                      pkgdata['packageFormat']['formatVersion'])
        else:
            try:
                shutil.copyfile(fromFilePath, toPath + toFile)
            except Exception as error:
                if type(error) == IOError:
                    raise IOError(error.args[0], error.args[1], os.path.basename(fromFilePath))
                else:
                    raise error

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
        response = HttpResponse(content_type='application/octetstream')
        with open(downloadPath() + path, 'rb') as pkg:
            response.write(pkg.read())
            response['Content-Length'] = pkg.tell()
        return response
    except:
        raise Http404


def categoryList(request):
    # this is not valid JSON, since we are returning a list!
    allmeta = [{'id': -1, 'name': 'All'}, ] #All metacategory
    categoryobject = Category.objects.all().order_by('order').values('id', 'name')
    categoryobject=allmeta + list(categoryobject)
    return JsonResponse(categoryobject, safe = False)


def categoryIcon(request):
    response = HttpResponse(content_type = 'image/png')
    categoryId = getRequestDictionary(request)['id']
    try:
        if categoryId != '-1':
            category = Category.objects.filter(id__exact = categoryId)[0]
            filename = iconPath() + "category_" + str(category.id) + ".png"
        else:
            from django.contrib.staticfiles import finders
            filename = finders.find('img/category_All.png')
        with open(filename, 'rb') as icon:
            response.write(icon.read())
            response['Content-Length'] = icon.tell()

    except:
        # In case there was error in searching for category,
        # return this image:
        # +-----+
        # |     |
        # |Error|
        # |     |
        # +-----+
        emptyPng  = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00 \x01\x03\x00\x00\x00I\xb4\xe8\xb7\x00\x00\x00\x06PLTE\x00\x00\x00\x00\x00\x00\xa5\x67\xb9\xcf\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\x33IDAT\x08\xd7\x63\xf8\x0f\x04\x0c\x0d\x0c\x0c\x8c\x44\x13\x7f\x40\xc4\x01\x10\x71\xb0\xf4\x5c\x2c\xc3\xcf\x36\xc1\x44\x86\x83\x2c\x82\x8e\x48\xc4\x5f\x16\x3e\x47\xd2\x0c\xc5\x46\x80\x9c\x06\x00\xa4\xe5\x1d\xb4\x8e\xae\xe8\x43\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82"
        response.write(emptyPng)

    return response
