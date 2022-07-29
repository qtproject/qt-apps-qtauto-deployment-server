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

import tarfile
import tempfile
import base64
import os
import hashlib
import hmac
import yaml
import magic

from django.conf import settings
from OpenSSL.crypto import load_pkcs12, FILETYPE_PEM, dump_privatekey, dump_certificate
from M2Crypto import SMIME, BIO, X509

from store.tags import SoftwareTagList, SoftwareTag
import store.osandarch

def makeTagList(pkgdata):
    """Generates tag lists out of package data
       First list - required tags, second list - conflicting tags
    """
    taglist = SoftwareTagList()
    tagconflicts = SoftwareTagList()
    for fields in ('extra', 'extraSigned'):
        if fields in pkgdata['header']:
            if 'tags' in pkgdata['header'][fields]:
                for i in list(pkgdata['header'][fields]['tags']):  # Fill tags list then add them
                    taglist.append(SoftwareTag(i))
            if 'conflicts' in pkgdata['header'][fields]:
                for i in list(pkgdata['header'][fields]['conflicts']):
                    tagconflicts.append(SoftwareTag(i))

    tags_hash = str(taglist) + str(tagconflicts)
    return taglist, tagconflicts, tags_hash

def getRequestDictionary(request):
    if request.method == "POST":
        return request.POST
    return request.GET

def packagePath(appId=None, architecture=None, tags=None):
    path = "packages" ## os.path.join(settings.MEDIA_ROOT, 'packages/')
    if tags is None:
        tags = ""
    if (appId is not None) and (architecture is not None):
        path = os.path.join(path, '_'.join([appId, architecture, tags]).replace('/', '_').\
            replace('\\', '_').replace(':', 'x3A').replace(',', 'x2C'))
    return path

def iconPath(appId=None, architecture=None, tags=None):
    path = "icons" ## os.path.join(settings.MEDIA_ROOT, 'icons/')
    if tags is None:
        tags = ""
    if (appId is not None) and (architecture is not None):
        return os.path.join(path, '_'.join([appId, architecture, tags]).replace('/', '_').\
            replace('\\', '_').replace(':', 'x3A').replace(',', 'x2C') + '.png')
    return path

def writeTempIcon(appId, architecture, tags, icon):
    try:
        path = os.path.join(settings.MEDIA_ROOT, iconPath())
        if not os.path.exists(path):
            os.makedirs(path)
        tempicon = open(os.path.join(settings.MEDIA_ROOT, iconPath(appId, architecture, tags)), 'wb')
        tempicon.write(icon)
        tempicon.flush()
        tempicon.close()
        return True, None
    except IOError as error:
        return False, 'Validation error: could not write icon file to media directory: %s' % \
            str(error)

def downloadPath():
    return os.path.join(settings.MEDIA_ROOT, 'downloads/')


def isValidFilesystemName(name, errorList):
    # see also in AM: src/common-lib/utilities.cpp / validateForFilesystemUsage

    try:
        # we need to make sure that we can use the name as directory in a filesystem and inode names
        # are limited to 255 characters in Linux. We need to subtract a safety margin for prefixes
        # or suffixes though:

        if not name:
            raise Exception('must not be empty')

        if len(name) > 150:
            raise Exception('the maximum length is 150 characters')

        # all characters need to be ASCII minus any filesystem special characters:
        spaceOnly = True
        forbiddenChars = '<>:"/\\|?*'
        for i, c in enumerate(name):
            if (ord(c) < 0x20) or (ord(c) > 0x7f) or (c in forbiddenChars):
                raise Exception(f'must consist of printable ASCII characters only, except any of \'{forbiddenChars}\'')

            if spaceOnly:
                spaceOnly = (c == ' ')

        if spaceOnly:
            raise Exception('must not consist of only white-space characters')

        return True

    except Exception as error:
        errorList[0] = str(error)
        return False

def verifySignature(signaturePkcs7, hash, chainOfTrust):
    # see also in AM: src/crypto-lib/signature.cpp / Signature::verify()

    s = SMIME.SMIME()

    bioSignature = BIO.MemoryBuffer(data = base64.decodestring(signaturePkcs7))
    signature = SMIME.load_pkcs7_bio(bioSignature)
    bioHash = BIO.MemoryBuffer(data = hash)
    certChain = X509.X509_Store()

    for trustedCert in chainOfTrust:
        bioCert = BIO.MemoryBuffer(data = trustedCert)

        while len(bioCert):
            cert = X509.load_cert_bio(bioCert, X509.FORMAT_PEM)
            certChain.add_x509(cert)

    s.set_x509_store(certChain)
    s.set_x509_stack(X509.X509_Stack())

    s.verify(signature, bioHash, SMIME.PKCS7_NOCHAIN)


def createSignature(hash, signingCertificatePkcs12, signingCertificatePassword):
    # see also in AM: src/crypto-lib/signature.cpp / Signature::create()

    s = SMIME.SMIME()

    # M2Crypto has no support for PKCS#12, so we have to use pyopenssl here
    # to load the .p12. Since the internal structures are incompatible, we
    # have to export from pyopenssl and import to M2Crypto via PEM BIOs.
    pkcs12 = load_pkcs12(signingCertificatePkcs12, signingCertificatePassword)
    signKey = BIO.MemoryBuffer(dump_privatekey(FILETYPE_PEM, pkcs12.get_privatekey()))
    signCert = BIO.MemoryBuffer(dump_certificate(FILETYPE_PEM, pkcs12.get_certificate()))
    caCerts = X509.X509_Stack()
    if pkcs12.get_ca_certificates():
        for cert in pkcs12.get_ca_certificates():
            bio = BIO.MemoryBuffer(dump_certificate(FILETYPE_PEM, cert))
            caCerts.push(X509.load_cert_bio(bio, X509.FORMAT_PEM))

    bioHash = BIO.MemoryBuffer(hash)

    s.load_key_bio(signKey, signCert)
    s.set_x509_stack(caCerts)
    signature = s.sign(bioHash, SMIME.PKCS7_DETACHED + SMIME.PKCS7_BINARY)
    bioSignature = BIO.MemoryBuffer()
    signature.write(bioSignature)

    data = bioSignature.read_all()
    return data


def parsePackageMetadata(packageFile):
    pkgdata = { }

    pkg = tarfile.open(fileobj=packageFile, mode='r:*', encoding='utf-8')

    fileCount = 0
    foundFooter = False
    footerContents = ''
    foundInfo = False
    foundIcon = False
    digest = hashlib.new('sha256')
    #Init magic sequence checker
    ms = magic.Magic()
    osset = set()
    archset = set()
    pkgfmt = set()

    packageHeaders = ['am-application', 'am-package']

    for entry in pkg:
        fileCount = fileCount + 1

        if not entry.isfile() and not entry.isdir():
            raise Exception('only files and directories are allowed: %s' % entry.name)
        elif entry.name.startswith('/'):
            raise Exception('no absolute paths are allowed: %s' % entry.name)
        elif entry.name.find('..') >= 0:
            raise Exception('no non-canonical paths are allowed: %s' % entry.name)
        elif 0 > entry.size > 2**31-1:
            raise Exception('file size > 2GiB: %s' % entry.name)
        elif entry.name.startswith('--PACKAGE-') and entry.isdir():
            raise Exception('all reserved entries (starting with --PACKAGE-) need to be files, found %s' % entry.name)

        contents = None
        if entry.isfile():
            try:
                contents = pkg.extractfile(entry).read()
            except Exception as error:
                raise Exception('Could not extract file %s: %s' % (entry.name, str(error)))

        if entry.name == '--PACKAGE-HEADER--':
            if fileCount != 1:
                raise Exception('file --PACKAGE-HEADER-- found at index %d, but it needs to be the first file in the package' % fileCount)

            try:
                docs = list(yaml.safe_load_all(contents))
            except yaml.YAMLError as error:
                raise Exception('Could not parse --PACKAGE-HEADER--: %s' % error)

            if len(docs) != 2:
                raise Exception('file --PACKAGE-HEADER-- does not consist of 2 YAML documents')
            if not (docs[0]['formatVersion'] in [1, 2] and docs[0]['formatType'] == 'am-package-header'):
                raise Exception('file --PACKAGE-HEADER-- has an invalid document type')

            # Set initial package format version from --PACKAGE-HEADER--
            # it must be consistent with info.yaml file
            pkgdata['packageFormat'] = docs[0]
            pkgdata['header'] = docs[1]
        elif fileCount == 1:
            raise Exception('the first file in the package is not --PACKAGE-HEADER--, but %s' % entry.name)

        if entry.name.startswith('--PACKAGE-FOOTER--'):
            footerContents += contents.decode('utf-8')

            foundFooter = True
        elif foundFooter:
            raise Exception('no normal files are allowed after the first --PACKAGE-FOOTER-- (found %s)' % entry.name)

        if not entry.name.startswith('--PACKAGE-'):
            addToDigest1 = '%s/%s/' % ('D' if entry.isdir() else 'F', 0 if entry.isdir() else entry.size)
            addToDigest1 = addToDigest1.encode('utf-8')
            entryName = entry.name
            if entry.isdir() and entryName.endswith('/'):
                entryName = entryName[:-1]
            addToDigest2 = str(entryName).encode('utf-8')

            if entry.isfile():
                digest.update(contents)
            digest.update(addToDigest1)
            digest.update(addToDigest2)

        if entry.name == 'info.yaml':
            if fileCount != 2:
                raise Exception('file info.yaml found at index %d, but it needs to be the second file of the package' % fileCount)

            try:
                docs = list(yaml.safe_load_all(contents))
            except yaml.YAMLError as error:
                raise Exception('Could not parse %s: %s' % (entry.name, error))

            if len(docs) != 2:
                raise Exception('file %s does not consist of 2 YAML documents' % entry.name)
            if docs[0]['formatVersion'] != 1 or not docs[0]['formatType'] in packageHeaders:
                raise Exception('file %s has an invalid document type' % entry.name)
            if (packageHeaders.index(docs[0]['formatType']) + 1) > pkgdata['packageFormat']['formatVersion']:
                raise Exception('inconsistent package version between --PACKAGE-HEADER-- and info.yaml files.')

            pkgdata['info'] = docs[1]
            pkgdata['info.type'] = docs[0]['formatType']
            foundInfo = True

        elif entry.name == 'icon.png':
            if fileCount != 3:
                raise Exception('file icon.png found at index %d, but it needs to be the third file in the package' % fileCount)
            pkgdata['icon'] = contents
            foundIcon = True

        elif not foundInfo and not foundIcon and fileCount >= 2:
            raise Exception('package does not start with info.yaml and icon.png - found %s' % entry.name)

        if fileCount > 2:
            if contents and entry.isfile():
                # check for file type here.
                fil = tempfile.NamedTemporaryFile() #This sequence is done to facilitate showing full type info
                fil.write(contents)                 #libmagic refuses to give full information when called with
                fil.seek(0)                         #from_buffer instead of from_file
                filemagic = ms.from_file(fil.name)
                fil.close()
                osarch = store.osandarch.getOsArch(filemagic)
                if osarch: #[os, arch, endianness, bits, fmt]
                    architecture = '-'.join(osarch[1:])
                    osset.add(osarch[0])
                    archset.add(architecture)
                    pkgfmt.add(osarch[4])
                    print(entry.name, osarch)

    # finished enumerating all files
    try:
        docs = list(yaml.safe_load_all(footerContents))
    except yaml.YAMLError as error:
        raise Exception('Could not parse %s: %s' % (entry.name, error))

    if len(docs) < 2:
        raise Exception('file --PACKAGE-FOOTER-- does not consist of at least 2 YAML documents')
    if not (docs[0]['formatVersion'] in [1, 2]) or docs[0]['formatType'] != 'am-package-footer':
        raise Exception('file --PACKAGE-FOOTER-- has an invalid document type')
    if docs[0]['formatVersion'] != pkgdata['packageFormat']['formatVersion']:
        raise Exception('inconsistent package version between --PACKAGE-HEADER-- and --PACKAGE-FOOTER-- files.')

    pkgdata['footer'] = docs[1]
    for doc in docs[2:]:
        pkgdata['footer'].update(doc)

    pkgdata['digest'] = digest.hexdigest()
    pkgdata['rawDigest'] = digest.digest()

    if len(osset) > 1:
        raise Exception('Package can not contain binaries for more than one OS')
    if len(archset) > 1:
        raise Exception('Multiple binary architectures detected in package')
    if len(pkgfmt) > 1:
        raise Exception('Multiple binary formats detected in package')
    if (not osset) and (not archset) and (not pkgfmt):
        pkgdata['architecture'] = 'All'
    else:
        pkgdata['architecture'] = list(archset)[0]
        pkgdata['binfmt'] = 'binfmt_' + list(pkgfmt)[0]

    pkg.close()
    return pkgdata


def parseAndValidatePackageMetadata(packageFile, certificates = []):
    pkgdata = parsePackageMetadata(packageFile)

    if pkgdata['packageFormat']['formatVersion'] == 1:
        packageIdKey = 'applicationId'
    elif pkgdata['packageFormat']['formatVersion'] == 2:
        packageIdKey = 'packageId'
    else:
        raise Exception('Unknown package formatVersion %s' % pkgdata['packageFormat']['formatVersion'])

    if pkgdata['info.type'] == 'am-package':
        infoList = ['id', 'name', 'icon', 'applications']
    elif pkgdata['info.type'] == 'am-application':
        infoList = ['id', 'name', 'icon', 'runtime', 'code']
    else:
        raise Exception('Unknown info.yaml formatType %s' % pkgdata['info.type'])



    partFields = { 'header': [ packageIdKey, 'diskSpaceUsed' ],
                   'info':   infoList,
                   'footer': [ 'digest' ],
                   'icon':   [],
                   'digest': [] }

    for part in list(partFields.keys()):
        if not part in pkgdata:
            raise Exception('package metadata is missing the %s part' % part)
        data = pkgdata[part]

        for field in partFields[part]:
            if field not in data:
                raise Exception('metadata %s is missing in the %s part' % (field, part))

    if pkgdata['header'][packageIdKey] != pkgdata['info']['id']:
        raise Exception('the id fields in --PACKAGE-HEADER-- and info.yaml are different: %s vs. %s' % (pkgdata['header'][packageIdKey], pkgdata['info']['id']))

    error = ['']
    if not isValidFilesystemName(pkgdata['info']['id'], error):
        raise Exception('invalid id: %s' % error[0])

    if pkgdata['header']['diskSpaceUsed'] <= 0:
        raise Exception('the diskSpaceUsed field in --PACKAGE-HEADER-- is not > 0, but %d' % pkgdata['header']['diskSpaceUsed'])

    if type(pkgdata['info']['name']) != type({}):
        raise Exception('invalid name: not a dictionary')

    name = ''
    if 'en' in pkgdata['info']['name']:
        name = pkgdata['info']['name']['en']
    elif 'en_US' in pkgdata['info']['name']:
        name = pkgdata['info']['name']['en_US']
    elif len(pkgdata['info']['name']) > 0:
        name = list(pkgdata['info']['name'].values())[0]

    if not name:
        raise Exception('could not deduce a suitable package name from the info part')

    try:
        _, _, _ = makeTagList(pkgdata)
    except BaseException as error:
        raise Exception(str(error))

    pkgdata['storeName'] = name

    if pkgdata['digest'] != pkgdata['footer']['digest']:
        raise Exception('digest does not match, is: %s, but should be %s' % (pkgdata['digest'], pkgdata['footer']['digest']))
    if 'storeSignature' in pkgdata['footer']:
        raise Exception('cannot upload a package with an existing storeSignature field')

    if not settings.APPSTORE_NO_SECURITY:
        if not 'developerSignature' in pkgdata['footer']:
            raise Exception('cannot upload a package without a developer signature')

        certificates = []
        for certFile in settings.APPSTORE_DEV_VERIFY_CA_CERTIFICATES:
            with open(certFile, 'rb') as cert:
                certificates.append(cert.read())

        verifySignature(pkgdata['footer']['developerSignature'], pkgdata['rawDigest'], certificates)

    return pkgdata


def addFileToPackage(sourcePackageFile, destinationPackageFile, fileName, fileContents):
    src = tarfile.open(sourcePackageFile, mode = 'r:*', encoding = 'utf-8')
    dst = tarfile.open(destinationPackageFile, mode = 'w:gz', encoding = 'utf-8')

    for entry in src:
        if entry.isfile():
            dst.addfile(entry, src.extractfile(entry))
        else:
            dst.addfile(entry)

    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(fileContents)
        tmp.seek(0)

        entry = dst.gettarinfo(fileobj = tmp, arcname = fileName)
        entry.uid = entry.gid = 0
        entry.uname = entry.gname = ''
        entry.mode = 0o400
        dst.addfile(entry, fileobj = tmp)

    dst.close()
    src.close()

def addSignatureToPackage(sourcePackageFile, destinationPackageFile, digest, deviceId, version=1):
    signingCertificate = ''
    with open(settings.APPSTORE_STORE_SIGN_PKCS12_CERTIFICATE) as cert:
        signingCertificate = cert.read()

    digestPlusId = hmac.new(deviceId, digest, hashlib.sha256).digest()
    signature = createSignature(digestPlusId, signingCertificate,
                                settings.APPSTORE_STORE_SIGN_PKCS12_PASSWORD)

    yamlContent = yaml.dump_all([{'formatVersion': version, 'formatType': 'am-package-footer'},
                                 {'storeSignature': base64.encodestring(signature)}],
                                explicit_start=True)

    addFileToPackage(sourcePackageFile, destinationPackageFile,
                     '--PACKAGE-FOOTER--store-signature', yamlContent)
