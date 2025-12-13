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
                    'name': 'Eleri Default Template',
                    'qfmt': '''
                        {{Sentence}}
                        <hr id="meta">
                        {{Word}} ({{Frequency}})
                    ''',
                    'afmt': '{{FrontSide}}<hr id="answer">{{Translation}}',
                },
            ],
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
