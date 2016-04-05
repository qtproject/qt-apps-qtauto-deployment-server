# -*- coding: utf-8 -*-
#############################################################################
##
## Copyright (C) 2016 Pelagicore AG
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

from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import store.models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='App',
            fields=[
                ('id', models.CharField(max_length=200, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('file', models.FileField(upload_to=store.models.content_file_name)),
                ('briefDescription', models.TextField()),
                ('description', models.TextField()),
                ('dateAdded', models.DateField(auto_now_add=True)),
                ('dateModified', models.DateField(auto_now=True)),
                ('rating', models.FloatField()),
                ('isTopApp', models.BooleanField(default=False)),
                ('price', models.DecimalField(max_digits=8, decimal_places=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('rank', models.SmallIntegerField(unique=True, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('user', models.ForeignKey(primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('name', models.CharField(max_length=200)),
                ('certificate', models.TextField(max_length=8000)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='app',
            name='category',
            field=models.ForeignKey(to='store.Category'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='app',
            name='vendor',
            field=models.ForeignKey(to='store.Vendor'),
            preserve_default=True,
        ),
    ]
