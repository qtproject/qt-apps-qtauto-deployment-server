#############################################################################
##
## Copyright (C) 2015 Pelagicore AG
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

import tarfile
import hashlib
import hmac
import yaml
import sys
import tarfile
import tempfile
import base64
import os

from M2Crypto import SMIME, BIO, X509
from OpenSSL.crypto import load_pkcs12, FILETYPE_PEM, dump_privatekey, dump_certificate

from django.conf import settings


def packagePath(appId = None):
    path = settings.MEDIA_ROOT + 'packages/'
    if appId is not None:
        return path + appId
    return path

def iconPath(appId = None):
    path = settings.MEDIA_ROOT + 'icons/'
    if appId is not None:
        return path + appId + '.png'
    return path

def downloadPath():
    return settings.MEDIA_ROOT + 'downloads/'


def isValidDnsName(dnsName, errorString):
    # see also in AM: src/common-lib/utilities.cpp / isValidDnsName()

    try:
        # this is not based on any RFC, but we want to make sure that this id is usable as filesystem
        # name. So in order to support FAT (SD-Cards), we need to keep the path < 256 characters

        if len(dnsName) > 200:
            raise Exception('too long - the maximum length is 200 characters')

        # we require at least 3 parts: tld.company-name.application-name
        # this make it easier for humans to identify apps by id.

        labels = dnsName.split('.')
        if len(labels) < 3:
            raise Exception('wrong format - needs to consist of at least three parts separated by .')

        # standard domain name requirements from the RFCs 1035 and 1123

        for label in labels:
            if 0 >= len(label) > 63:
                raise Exception('wrong format - each part of the name needs to at least 1 and at most 63 characters')

            for i, c in enumerate(label):
                isAlpha = (c >= '0' and c <= '9') or (c >= 'a' and c <= 'z');
                isDash  = (c == '-');
                isInMiddle = (i > 0) and (i < (len(label) - 1));

                if not (isAlpha or (isDash and isInMiddle)):
                    raise Exception('invalid characters - only [a-z0-9-] are allowed (and '-' cannot be the first or last character)')

        return True

    except Exception as error:
        errorString = str(error)
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

    pkg = tarfile.open(fileobj=packageFile, mode='r:*', encoding='utf-8');

    fileCount = 0
    foundFooter = False
    footerContents = ''
    foundInfo = False
    foundIcon = False
    digest = hashlib.new('sha256')

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
            if docs[0]['formatVersion'] != 1 or docs[0]['formatType'] != 'am-package-header':
                raise Exception('file --PACKAGE-HEADER-- has an invalid document type')

            pkgdata['header'] = docs[1]
        elif fileCount == 1:
            raise Exception('the first file in the package is not --PACKAGE-HEADER--, but %s' % entry.name)

        if entry.name.startswith('--PACKAGE-FOOTER--'):
            footerContents += contents

            foundFooter = True
        elif foundFooter:
            raise Exception('no normal files are allowed after the first --PACKAGE-FOOTER-- (found %s)' % entry.name)

        if not entry.name.startswith('--PACKAGE-'):
            addToDigest1 = '%s/%s/' % ('D' if entry.isdir() else 'F', 0 if entry.isdir() else entry.size)
            entryName = entry.name
            if entry.isdir() and entryName.endswith('/'):
                entryName = entryName[:-1]
            entryName = os.path.basename(entryName)
            addToDigest2 = unicode(entryName, 'utf-8').encode('utf-8')

            ## print >>sys.stderr, addToDigest1
            ## print >>sys.stderr, addToDigest2

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
            if docs[0]['formatVersion'] != 1 or docs[0]['formatType'] != 'am-application':
                raise Exception('file %s has an invalid document type' % entry.name)

            pkgdata['info'] = docs[1]
            foundInfo = True

        elif entry.name == 'icon.png':
            if fileCount != 3:
                raise Exception('file icon.png found at index %d, but it needs to be the third file in the package' % fileCount)
            pkgdata['icon'] = contents
            foundIcon = True

        elif not foundInfo and not foundInfo and fileCount >= 2:
            raise Exception('package does not start with info.yaml and icon.png - found %s' % entry.name)

    # finished enumerating all files
    try:
        docs = list(yaml.safe_load_all(footerContents))
    except yaml.YAMLError as error:
        raise Exception('Could not parse %s: %s' % (entry.name, error))

    if len(docs) < 2:
        raise Exception('file --PACKAGE-FOOTER-- does not consist of at least 2 YAML documents')
    if docs[0]['formatVersion'] != 1 or docs[0]['formatType'] != 'am-package-footer':
        raise Exception('file --PACKAGE-FOOTER-- has an invalid document type')

    pkgdata['footer'] = docs[1]
    for doc in docs[2:]:
        pkgdata['footer'].update(doc)

    pkgdata['digest'] = digest.hexdigest()
    pkgdata['rawDigest'] = digest.digest()

    pkg.close()
    return pkgdata


def parseAndValidatePackageMetadata(packageFile, certificates = []):
    pkgdata = parsePackageMetadata(packageFile)

    partFields = { 'header': [ 'applicationId', 'diskSpaceUsed' ],
                   'info':   [ 'id', 'name', 'icon' ],
                   'footer': [ 'digest' ],
                   'icon':   [],
                   'digest': [] }

    for part in partFields.keys():
        if not part in pkgdata:
            raise Exception('package metadata is missing the %s part' % part)
        data = pkgdata[part]

        for field in partFields[part]:
            if field not in data:
                raise Exception('metadata %s is missing in the %s part' % (field, part))

    if pkgdata['header']['applicationId'] != pkgdata['info']['id']:
        raise Exception('the id fields in --PACKAGE-HEADER-- and info.yaml are different: %s vs. %s' % (pkgdata['header']['applicationId'], pkgdata['info']['id']))

    error = ''
    if not isValidDnsName(pkgdata['info']['id'], error):
        raise Exception('invalid id: %s' % error)

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
        name = pkgdata['info']['name'].values()[0]

    if len(name) == 0:
        raise Exception('could not deduce a suitable package name from the info part')

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
        entry.mode = 0400
        dst.addfile(entry, fileobj = tmp)

    dst.close()
    src.close()

def addSignatureToPackage(sourcePackageFile, destinationPackageFile, digest, deviceId):
    signingCertificate = ''
    with open(settings.APPSTORE_STORE_SIGN_PKCS12_CERTIFICATE) as cert:
        signingCertificate = cert.read()

    digestPlusId = hmac.new(deviceId, digest, hashlib.sha256).digest();
    signature = createSignature(digestPlusId, signingCertificate, settings.APPSTORE_STORE_SIGN_PKCS12_PASSWORD)

    yamlContent = yaml.dump_all([{ 'formatVersion': 1, 'formatType': 'am-package-footer'}, { 'storeSignature': base64.encodestring(signature) }], explicit_start=True)

    addFileToPackage(sourcePackageFile, destinationPackageFile, '--PACKAGE-FOOTER--store-signature', yamlContent)
