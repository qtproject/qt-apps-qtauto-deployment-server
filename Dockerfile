
FROM debian:bullseye-slim
MAINTAINER Robert Griebl <robert.griebl@qt.io>

ENV LC_ALL="C.UTF-8"

RUN apt-get update && apt-get install -y --no-install-recommends \
  python3-pip \
  python3-magic \
  python3-m2crypto

RUN rm -rf /var/lib/apt/lists/*

COPY requirements.txt /
RUN pip3 install -r requirements.txt

RUN mkdir /server
COPY manage.py /server
RUN chmod 755 ./server/manage.py
COPY appstore/ /server/appstore
COPY store/ /server/store

RUN mkdir /data
VOLUME /data

ENV APPSTORE_DATA_PATH=/data
ENV APPSTORE_STORE_SIGN_PKCS12_CERTIFICATE /data/certificates/store.p12
ENV APPSTORE_DEV_VERIFY_CA_CERTIFICATES    /data/certificates/ca.crt,/data/certificates/devca.crt

# You can also set these environment variables:
## ENV APPSTORE_PLATFORM_ID                   NEPTUNE3
## ENV APPSTORE_PLATFORM_VERSION              2
## ENV APPSTORE_DOWNLOAD_EXPIRY               10
## ENV APPSTORE_BIND_TO_DEVICE_ID             1
## ENV APPSTORE_NO_SECURITY                   1
## ENV APPSTORE_STORE_SIGN_PKCS12_CERTIFICATE certificates/store.p12
## ENV APPSTORE_STORE_SIGN_PKCS12_PASSWORD    password
## ENV APPSTORE_DEV_VERIFY_CA_CERTIFICATES    certificates/ca.crt,certificates/devca.crt


COPY docker-entrypoint.sh /
ENTRYPOINT [ "/docker-entrypoint.sh" ]
CMD [ "runserver", "0.0.0.0:8080" ]

EXPOSE 8080
