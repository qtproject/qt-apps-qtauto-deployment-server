from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'appstore.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'^hello$',             'store.api.hello'),
    url(r'^login$',             'store.api.login'),
    url(r'^logout$',            'store.api.logout'),
    url(r'^app/list$',          'store.api.appList'),
    url(r'^app/icon',           'store.api.appIcon'),
    url(r'^app/description',    'store.api.appDescription'),
    url(r'^app/purchase',       'store.api.appPurchase'),
    url(r'^app/download/(.*)$', 'store.api.appDownload'),
    url(r'^category/list$',     'store.api.categoryList'),
    url(r'^category/icon$',     'store.api.categoryIcon'),
)
