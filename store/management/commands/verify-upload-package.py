import sys

from django.core.management.base import BaseCommand, CommandError

from store.utilities import parseAndValidatePackageMetadata

class Command(BaseCommand):
    help = 'Checks if packages are valid for store upload'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Usage: manage.py verify-upload-package <package>')

        try:
            self.stdout.write('Parsing package %s' % args[0])
            packageFile = open(args[0], 'rb')
            pkgdata = parseAndValidatePackageMetadata(packageFile)

            self.stdout.write('  -> passed validation (internal name: %s)\n' % pkgdata['storeName'])

        except Exception as error:
            self.stdout.write('  -> failed: %s\n' % str(error))
