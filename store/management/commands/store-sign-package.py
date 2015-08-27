import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from store.utilities import parseAndValidatePackageMetadata, addSignatureToPackage

class Command(BaseCommand):
    help = 'Adds a store signature to the package'

    def handle(self, *args, **options):
        if 2 > len(args) > 3:
            raise CommandError('Usage: manage.py store-sign-package <source package> <destination-package> [device id]')

        sourcePackage = args[0]
        destinationPackage = args[1]
        deviceId = args[2] if len(args) == 3 else ''

        try:
            self.stdout.write('Parsing package %s' % sourcePackage)
            packageFile = open(sourcePackage, 'rb')
            pkgdata = parseAndValidatePackageMetadata(packageFile)
            self.stdout.write('  -> passed validation (internal name: %s)\n' % pkgdata['storeName'])

            self.stdout.write('Adding signature to package %s' % destinationPackage)
            addSignatureToPackage(sourcePackage, destinationPackage, pkgdata['rawDigest'], deviceId)
            self.stdout.write('  -> finished')

        except Exception as error:
            self.stdout.write('  -> failed: %s\n' % str(error))
            raise
