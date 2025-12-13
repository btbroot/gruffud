from locale import normalize

from django.core.management.base import BaseCommand
from genanki import Deck, Model, Note, Package
from pydash import order_by

from eleri.models import Word


DECK_ID = 2059400110
MODEL_ID = 1607392319
OUTPUT = 'eleri.apkg'



class Command(BaseCommand):
    help = "Export sentences into an Anki 2.1 deck (.apkg)"

    def add_arguments(self, parser):
        parser.add_argument(
            'first_language',
            type=str,
            help='Language code of the dictionary words',
        )
        parser.add_argument(
            'second_language',
            type=str,
            help='Language code of the translation',
        )

    def handle(self, *args, **options):
        locale = normalize(options['first_language']).split('.')[0]
        model = Model(
            model_id=MODEL_ID,
            name='Eleri Default Model',
            fields=[
                {'name': 'Word'},
                {'name': 'Frequency'},
                {'name': 'Sentence'},
                {'name': 'Translation'},
            ],
            templates=[
                {
                    'name': 'Eleri Default Note',
                    'qfmt': f'''
                        <div class="meta">{{{{Word}}}} ({{{{Frequency}}}})</div>
                        <hr>
                        {{{{Sentence}}}}
                        <br>
                        {{{{tts {locale}:Sentence}}}}
                    ''',
                    'afmt': '{{FrontSide}}<hr>{{Translation}}',
                },
            ],
            css='''
                .meta{
                    font-size: smaller;
                    font-style: italic;
                    color: gray;
                }
            '''
        )
        deck = Deck(deck_id=DECK_ID, name='Eleri Default Deck')
        count = 0
        for word in Word.objects.filter(
            language=options['first_language'],
            sentence__translations__language=options['second_language'],
        ).order_by('-frequency'):
            deck.add_note(
                Note(
                    model=model,
                    fields=[
                        word.form,
                        str(word.frequency),
                        word.sentence_set.first().text,
                        word.sentence_set.first().translations.first().text,
                    ],
                )
            )
            count += 1
        Package(deck).write_to_file(OUTPUT)
        self.stdout.write(
            self.style.SUCCESS(f"Exported {count} notes to {OUTPUT}")
        )
