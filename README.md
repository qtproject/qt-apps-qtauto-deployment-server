This is a PoC deployment server, which can be used together with
the Neptune IVI UI and the Pelagicore Application Manager.

**This is a development server only - do NOT use in production.**

Architecture
============

Setting up the server in virtualenv:

virtualenv ./venv
./venv/bin/pip install -r requirements.txt

(libffi-dev is also needed)


The server is based on Python/Django.
The reference platform is Debian Jessie and the packages needed there are:

  * python (2.7.9)
  * python-yaml (3.11)
  * python-django (1.7.9)
  * python-django-common (1.7.9)
  * python-openssl (0.14)
  * python-m2crypto (0.21)

Before running the server, make sure to adapt the `APPSTORE_*` settings in
`appstore/settings.py` to your environment.

Since package downloads are done via temporary files, you need to setup
a cron-job to cleanup these temporary files every now and then. The job
should be triggerd every (`settings.APPSTORE_DOWNLOAD_EXPIRY` / 2) minutes
and it just needs to execute:

```
  ./manage.py expire-downloads
```

Commands
========

*   Running the server:
    ```
    ./manage.py runserver 0.0.0.0:8080
    ```
    will start the server on port 8080, reachable for anyone. You can tweak
    the listening address to whatever fits your needs.

*   Cleaning up the downloads directory:
    ```
    ./manage.py expire-downloads
    ```
    will remove all files from the downloads/ directory, that are older than
    `settings.APPSTORE_DOWNLOAD_EXPIRY` minutes.
    This should be called from a cron-job (see above).

*   Manually verifying a package for upload:
    ```
    ./manage.py verify-upload-package <pkg.appkg>
    ```
    will tell you if `<pkg.appkg>` is a valid package that can be uploaded to
    the store.

*   Manually adding a store signature to a package:
    ```
    ./manage.py store-sign-package <in.appkg> <out.appkg> [device id]
    ```
    will first verify `<in.appkg>`. If this succeeds, it will copy `<in.appkg>`
    to `<out.appkg>` and add a store signature. The optional `[device id]`
    parameter will lock the generated package to the device with this id.

HTTP API
========

The deployment server exposes a HTTP API to the world. Arguments to the
functions need to be provided using the HTTP GET syntax. The returned data
will be JSON, PNG or text, depending on the function

Basic workflow:

1.  Send a `"hello"` request to the server to get the current status and check
    whether your platform is compatible with this server instance:
    ```
    http://<server>/hello?platform=AM&version=1
    ```
    Returns:
    ```
    { "status": "ok" }
    ```

2.  Login as user `'user'` with password `'pass'`:
    ```
    http://<server>/login?username=user&password=pass
    ```
    Returns:
    ```
    { "status": "ok" }
    ```

3.  List all applications
    ```
    http://<server>/app/list
    ```
    Returns:
    ```
    [{ "category": "Entertainment",
       "name": "Nice App",
       "vendor": "Pelagicore",
       "briefDescription": "Nice App is a really nice app.",
       "category_id": 4,
       "id": "com.pelagicore.niceapp"},
     ...
    ]
    ```

4.  Request a download for a App:
    ```
    http://<server>/app/purchase?device_id=12345&id=com.pelagicore.niceapp
    ```
    Returns:
   ```
    { "status": "ok",
      "url": "http://<server>/app/download/com.pelagicore.niceapp.2.npkg",
      "expiresIn": 600
    }
   ```

5. Use the `'url'` provided in step 4 to download the application within
   `'expiresIn'` seconds.


API Reference
=============

## hello
Checks whether you are using the right Platform and the right API to communicate with the Server.

| Parameter  | Description |
| ---------- | ----------- |
| `platform` | The platform the client is running on, this sets the architecture of the packages you get. (see `settings.APPSTORE_PLATFORM`) |
| `version`  | The Deployment Server HTTP API version you are using to communicate with the server. (see `settings.APPSTORE_VERSION`) |
| `require_tag` | Optional parameter for filtering packages by tags. Receives coma-separated list of tags. Only applications containing any of specified tags should be listed. Tags must be alphanumeric. |
| `conflicts_tag` | Optional parameter for filtering packages by tags. Receives coma-separated list of tags. No application containing any of the tags should be listed. Tags must be alphanumeric. |

Returns a JSON object:

| JSON field | Value     | Description |
| ---------- | --------- | ----------- |
| `status`   | `ok`      | Successfull. |
|            | `maintenance` | The Server is in maintenance mode and can't be used at the moment. |
|            | `incompatible-platform` | You are using an incompatible Platform. |
|            | `incompatible-version` | You are using an incompatible Version of the API. |
|            | `malformed-tag` | Tag had wrong format, was not alphanumeric or could not be parsed. |

## login
Does a login on the Server with the given username and password. Either a imei or a mac must be provided. This call is needed for downloading apps.

| Parameter  | Description |
| ---------- | ----------- |
| `username` | The username. |
| `password` | The password for the given username |

Returns a JSON object:

| JSON field | Value     | Description |
| ---------- | --------- | ----------- |
| `status`   | `ok`      | Successfull. |
|            | `missing-credentials` | Forgot to provided username and/or password. |
|            | `account-disabled` | The account is disabled. |
|            | `authentication-failed` | Failed to authenticate with given username and password. |


## logout
Does a logout on the Server for the currently logged in user.

Returns a JSON object:

| JSON field | Value     | Description |
| ---------- | --------- | ----------- |
| `status`   | `ok`      | Successfull. |
|            | `failed`  | Not logged in. |

## app/list
Lists all apps. The returned List can be filtered by using the category_id and the filter argument.

| Parameter     | Description |
| ------------- | ----------- |
| `category_id` | Only lists apps, which are in the category with this id. |
| `filter`      | Only lists apps, whose name matches the filter. |

Returns a JSON array (not an object!). Each field is a JSON object:

| JSON field         | Description |
| ------------------ | ----------- |
| `id`               | The unique id of the application |
| `name`             | The name of the application |
| `vendor`           | The name of the vendor of this application
| `briedDescription` | A short (one line) description of the application
| `category`         | The name of the category the application is in
| `category_id`      | The id of the category the application is in

## app/icon
 Returns an icon for the given application id.

| Parameter  | Description |
| ---------- | ----------- |
| `id`       | The application id |

 Returns a PNG image or a 404 error


## app/description
Returns a description for the given application id.

| Parameter  | Description |
| ---------- | ----------- |
| `id`       | The application id |

Returns text - either HTML or plain


## app/purchase
Returns an url which can be used for downloading the requested application for
certain period of time (configurable in the settings)

| Parameter   | Description |
| ----------- | ----------- |
| `device_id` | The unique device id of the client hardware. |
| `id`        | The application Id. |

Returns a JSON object:

| JSON field  | Value     | Description |
| ----------- | --------- | ----------- |
| `status`    | `ok`      | Successfull. |
|             | `failed`  | Something went wrong. See the `error` field for more information. |
| `error`     | **text**  | An error description, if `status` is `failed. |
| `url`       | **url**   | The url which can now be used for downloading the application. |
| `expiresIn` | **int**   | The time in seconds the url remains valid. |

## category/list
Lists all the available categories. It uses the rank stored on the server for ordering.

Returns a JSON array (not an object!). Each field is a JSON object:

| JSON field | Description |
| ---------- | ----------- |
| `id`       | The unique id of the category |
| `name`     | The name of the category |

## category/icon:
Returns an icon for the given category id.

| Parameter  | Description |
| ---------- | ----------- |
| `id`       | The id of the category |

Returns a PNG image or a 404 error
