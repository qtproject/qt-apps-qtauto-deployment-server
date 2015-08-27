import os
import time

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from store.utilities import downloadPath

class Command(BaseCommand):
    help = 'Expires all downloads that are older than 10 minutes'

    def handle(self, *args, **options):
        self.stdout.write('Removing expired download packages')
        pkgPath = downloadPath()
        if not os.path.exists(pkgPath):
            os.makedirs(pkgPath)

        for pkg in os.listdir(pkgPath):
            t = os.path.getmtime(pkgPath + pkg)
            age = time.time() - t
            if age > (10 * 60):
               os.remove(pkgPath + pkg)
               self.stdout.write(' -> %s (age: %s seconds)' % (pkg, int(age)))

        self.stdout.write('Done')
