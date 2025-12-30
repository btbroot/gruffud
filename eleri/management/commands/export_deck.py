from hashlib import sha256
from locale import normalize

from django.conf import settings
from django.core.management.base import BaseCommand
from genanki import Deck, Model, Note, Package
from regex import TEMPLATE

from eleri import VERSION
from eleri.models import Word


DECKS = [
    'eleri_deck_frequency_list-fi_ru',
    'eleri_deck_phrasal_verbs-en_ru',
]
LANG1 = '''
    <div class="meta">{{{{Word}}}} ({{{{Frequency}}}})<hr></div>
    {{{{Sentence}}}}<br>{{{{tts {locale}:Sentence}}}}
'''
LANG2 = '{{{{Translation}}}}'
MODEL = 'eleri_model-{language}-0.1'
TEMPLATE = {
    'fields': [
        {'name': 'Word'},
        {'name': 'Frequency'},
        {'name': 'Sentence'},
        {'name': 'Translation'},
    ],
    'templates': [
        {
            'name': 'Recognition',
            'qfmt': LANG1,
            'afmt': '{{{{FrontSide}}}}<hr>' + LANG2,
        },
        {
            'name': 'Production',
            'qfmt': LANG2,
            'afmt': '{{{{FrontSide}}}}<hr>' + LANG1,
        },
    ],
    'css': '.meta {font-size: smaller; font-style: italic; color: gray;}',
}
SUFFIX = '.apkg'
MAX = 2 ** 63 - 1


class Command(BaseCommand):
    help = "Export sentences into an Anki 2.1 deck (.apkg)"

    def anki_id(self, name):
        result = int.from_bytes(sha256(name.encode()).digest()) % MAX
        self.stdout.write(f'Generated Anki ID {result} for name "{name}"')
        return result

    def add_arguments(self, parser):
        parser.add_argument(
            'deck',
            type=str,
            choices=DECKS,
            help='Which deck to export',
        )

    def handle(self, *args, **options):
        languages = options['deck'].split('-')[1].split('_')
        for template in TEMPLATE['templates']:
            for key in 'qfmt', 'afmt':
                template[key] = template[key].format(
                    locale=normalize(languages[0]).split('.')[0]
                )
        deck = Deck(deck_id=self.anki_id(options['deck']), name=options['deck'])
        model_name = MODEL.format(language=languages[0])
        model = Model(
            model_id=self.anki_id(model_name),
            name=model_name,
            fields=TEMPLATE['fields'],
            templates=TEMPLATE['templates'],
            css=TEMPLATE['css'],
        )
        count = 0
        for word in Word.objects.filter(
            language=languages[0],
            sentence__translations__language=languages[1],
        ).order_by('-frequency', '-lemma__frequency'):
            frequency = f'''
                {'na' if word.frequency is None else word.frequency} /
                {
                    'na' if word.lemma is None or word.lemma.frequency is None
                    else word.lemma.frequency
                }
            '''
            deck.add_note(
                Note(
                    model=model,
                    fields=[
                        word.form,
                        frequency,
                        word.sentence_set.first().text,
                        word.sentence_set.first().translations.first().text,
                    ],
                )
            )
            count += 1
        self.stdout.write(f'Prepared {count} notes')
        output = f'{options['deck']}-{VERSION}{SUFFIX}'
        Package(deck).write_to_file(output)
        self.stdout.write(
            self.style.SUCCESS(f'Exported {count} notes to {output}')
        )
