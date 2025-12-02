'''
Management command to import Finnish word frequency data into the Word model.

This command reads a text file containing corpus frequency information with lines
formatted as:

    1 552162 ja (3.1363 %)

Where:
- Column 1: index (ignored)
- Column 2: raw count (ignored)
- Column 3: word form (stored in Word.form)
- Column 4: frequency percentage in parentheses (normalized to a fraction and
  stored in Word.frequency)

The command ensures that a Language record for Finnish ('fi') exists, then
creates Word entries linked to that language. Data is inserted in batches using
bulk_create for efficiency, making it suitable for very large files (millions of
lines).

Usage:
    manage.py bulk_import_finnish

On completion, the Word table will contain normalized frequency values (0–1) for
each Finnish word form, enabling statistical analysis and lexicon queries.
'''

from re import compile
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from eleri.models import Language, Word


INPUT = (
    settings.BASE_DIR /
    '..' /
    'data' /
    'Frequency-List-of-Written-Finnish-Word-Forms' /
    'parole_frek.txt'
)
ENCODING = 'latin-1'
FORM = 'form'
FREQ = 'freq'
RE = rf'\d+ \d+ (?P<{FORM}>[\w\-:]+) \((?P<{FREQ}>\d+\.\d+(?:e-\d+)?)'
TRASH = 'bulk_import_finnish_trash'

class Command(BaseCommand):
    help = 'Import Finnish words from corpus file'

    def handle(self, *args, **options):
        regexp = compile(RE)
        fi_lang, _ = Language.objects.get_or_create(
            code='fi',
            defaults={'name': 'Finnish'},
        )
        bulk = []
        with (
            open(file=INPUT, encoding=ENCODING) as f,
            open(file=TRASH, mode='w') as t,
        ):
            for i, line in enumerate(iterable=f, start=1):
                groups = regexp.search(line)
                if not groups:
                    self.stdout.write(
                        self.style.WARNING(f'Line {i} did not parse.')
                    )
                    print(line.strip(), file=t)
                    continue
                bulk.append(
                    Word(
                        language=fi_lang,
                        form=groups[FORM],
                        frequency=float(groups[FREQ]) / 100,
                    )
                )
        if bulk:
            self.stdout.write(f'Bulk creating.')
            with transaction.atomic():
                Word.objects.bulk_create(objs=bulk, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS('Import finished'))
