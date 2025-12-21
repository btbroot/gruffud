'''
Management command to import English phrasal verb frequency data into the Lemma
model.

This command reads a text file containing Appendix table with frequency
information with lines formatted as:

    1 GO on 14,903 2.9 2.9 0.14 0.14

Where:
- Column 1: rank (ignored)
- Column 2: verb lemma (stored in Lemma.headword along the particle)
- Column 3: particle (see the above)
- Column 4: token frequency (absolute, stored in Lemma.frequency)
- The rest is ignored

The command ensures that a Language record for English ('en') exists, then
creates Lemma entries linked to that language. Data is inserted in batches using
bulk_create for efficiency, making it suitable for very large files (millions of
lines).

Usage:
    manage.py bulk_import_davies

On completion, the Lemma table will contain absolute frequency values for
each English phrasal verb, enabling statistical analysis and lexicon queries. '''

from pathlib import Path
from re import compile
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from eleri.models import Lemma


INPUT = Path(
    settings.BASE_DIR /
    'data' /
    'Frequency-and-Coverage-of-Top-100-Phrasal-Verb-Lemmas-in-BNC',
    'davies_31.pdf.txt',
)
START = r'Rank Verb AVP # % of PV Cum % of PV % of LV Cum % of LV'
VERB_FIELD = 'verb'
PARTICLE_FIELD = 'part'
FREQ_FIELD = 'freq'
RE = rf'\d+ (?P<{VERB_FIELD}>\w+) (?P<{PARTICLE_FIELD}>\w+) (?P<{FREQ_FIELD}>[\d,]+) '
LANG= 'en'


class Command(BaseCommand):
    help = 'Import English phrasal verbs from Davies file'

    def handle(self, *args, **options):
        regexp = compile(RE)
        bulk = []
        with open(INPUT) as ingress:
            is_started = False
            for index, line in enumerate(iterable=ingress, start=1):
                if not is_started:
                    is_started = line.startswith(START)
                    continue
                groups = regexp.match(line)
                if not groups:
                    continue
                lemma = f'{groups[VERB_FIELD]} {groups[PARTICLE_FIELD]}'
                bulk.append(
                    Lemma(
                        language=LANG,
                        headword=lemma.lower(),
                        frequency=int(groups[FREQ_FIELD].replace(',', '')),
                    )
                )
        self.stdout.write(f'Bulk creating.')
        with transaction.atomic():
            Lemma.objects.bulk_create(bulk)
        self.stdout.write(self.style.SUCCESS('Import finished'))
