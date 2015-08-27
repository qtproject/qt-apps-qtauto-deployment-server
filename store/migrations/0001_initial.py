# -*- coding: utf-8 -*-
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
