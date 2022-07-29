#!/bin/sh

#export APPSTORE_PLATFORM_ID                   NEPTUNE3
#export APPSTORE_PLATFORM_VERSION              2
#export APPSTORE_DOWNLOAD_EXPIRY               10
#export APPSTORE_BIND_TO_DEVICE_ID             1
#export APPSTORE_NO_SECURITY                   1
#export APPSTORE_STORE_SIGN_PKCS12_CERTIFICATE certificates/store.p12
#export APPSTORE_STORE_SIGN_PKCS12_PASSWORD    password
#export APPSTORE_DEV_VERIFY_CA_CERTIFICATES    certificates/ca.crt,certificates/devca.crt

IT=""
if [ "x$1" = "x-it" ]; then
  shift
  IT=-it
fi

cd `dirname $0`/..
mkdir -p data

exec docker run $IT \
    -p 8080:8080 \
    -v `pwd`/data:/data \
    -e APPSTORE_PLATFORM_ID \
    -e APPSTORE_PLATFORM_VERSION \
    -e APPSTORE_DOWNLOAD_EXPIRY \
    -e APPSTORE_BIND_TO_DEVICE_ID \
    -e APPSTORE_NO_SECURITY \
    -e APPSTORE_STORE_SIGN_PKCS12_CERTIFICATE \
    -e APPSTORE_STORE_SIGN_PKCS12_PASSWORD \
    -e APPSTORE_DEV_VERIFY_CA_CERTIFICATES \
    qtauto-deployment-server "$@"
