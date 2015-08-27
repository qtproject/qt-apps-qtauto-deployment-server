import os

from django import forms
from django.conf import settings
from django.conf.urls import patterns
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy

from store.models import *
from utilities import parseAndValidatePackageMetadata
from utilities import iconPath


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'move')
    ordering = ('rank',)

    def save_model(self, request, obj, form, change):
        obj.save()

    def name(self, obj):
        # just to forbid sorting by name
        return obj.name
    name.short_description = ugettext_lazy('Item caption')

    def move(sefl, obj):
        """
        Returns html with links to move_up and move_down views.
        """
        button = u'<a href="%s"><img src="%simg/admin/arrow-%s.gif" /> %s</a>'
        prefix = settings.STATIC_URL

        link = '%d/move_up/' % obj.pk
        html = button % (link, prefix, 'up', _('up')) + " | "
        link = '%d/move_down/' % obj.pk
        html += button % (link, prefix, 'down', _('down'))
        return html
    move.allow_tags = True
    move.short_description = ugettext_lazy('Move')

    def get_urls(self):
        admin_view = self.admin_site.admin_view
        urls = patterns('',
            (r'^(?P<item_pk>\d+)/move_up/$', admin_view(self.move_up)),
            (r'^(?P<item_pk>\d+)/move_down/$', admin_view(self.move_down)),
        )
        return urls + super(CategoryAdmin, self).get_urls()

    def move_up(self, request, item_pk):
        """
        Decrease rank (change ordering) of the menu item with
        id=``item_pk``.
        """
        if self.has_change_permission(request):
            item = get_object_or_404(Category, pk=item_pk)
            item.decrease_rank()
        else:
            raise PermissionDenied
        return redirect('admin:appstore_category_changelist')

    def move_down(self, request, item_pk):
        """
        Increase rank (change ordering) of the menu item with
        id=``item_pk``.
        """
        if self.has_change_permission(request):
            item = get_object_or_404(Category, pk=item_pk)
            item.increase_rank()
        else:
            raise PermissionDenied
        return redirect('admin:appstore_category_changelist')


class AppAdminForm(forms.ModelForm):
    class Meta:
        exclude = ["id", "name"]

    appId = ""
    name = ""

    def clean(self):
        cleaned_data = super(AppAdminForm, self).clean()
        file = cleaned_data.get('file');

        # validate package
        pkgdata = None;
        try:
            chainOfTrust = []
            for cert in settings.APPSTORE_DEV_VERIFY_CA_CERTIFICATES:
                with open(cert, 'rb') as file:
                    chainOfTrust.append(file.read())

            pkgdata = parseAndValidatePackageMetadata(file, chainOfTrust)
        except Exception as error:
            raise forms.ValidationError(_('Validation error: %s' % str(error)))

        self.appId = pkgdata['info']['id'];
        self.name = pkgdata['storeName'];

        try:
            a = App.objects.get(name__exact = self.name)
            if a.id != pkgdata['info']['id']:
                raise forms.ValidationError(_('Validation error: the same package name (%s) is already used for application %s' % (self.name, a.id)))
        except App.DoesNotExist:
            pass

        # check if this really is an update
        if hasattr(self, 'instance') and self.instance.id:
            if self.appId != self.instance.id:
                raise forms.ValidationError(_('Validation error: an update cannot change the application id, tried to change from %s to %s' % (self.instance.id, self.appId)))
        else:
            try:
                if App.objects.get(id__exact = self.appId):
                    raise forms.ValidationError(_('Validation error: another application with id %s already exists' % str(self.appId)))
            except App.DoesNotExist:
                pass

        # write icon into file to serve statically
        try:
            if not os.path.exists(iconPath()):
                os.makedirs(iconPath())
            tempicon = open(iconPath(self.appId), 'w')
            tempicon.write(pkgdata['icon'])
            tempicon.flush()
            tempicon.close()

        except IOError as error:
            raise forms.ValidationError(_('Validation error: could not write icon file to media directory: %s' % str(error)))

        return cleaned_data

    def save(self, commit=False):
        m = super(AppAdminForm, self).save(commit);
        m.id = self.appId
        m.name = self.name
        return m


class AppAdmin(admin.ModelAdmin):
    form = AppAdminForm
    list_display = ('name',)

    def save_model(self, request, obj, form, change):
        obj.save()


admin.site.register(Category, CategoryAdmin)
admin.site.register(Vendor)
admin.site.register(App, AppAdmin)
