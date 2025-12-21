from locale import normalize

from django.conf import settings
from django.core.management.base import BaseCommand
from genanki import Deck, Model, Note, Package
from pydash import order_by

from eleri.models import Word


OUTPUT = 'eleri-{id}.apkg'
MODEL_ID = 1607392319
DECK_ID = {'fi': 2059400110, 'en': 2059400111 }


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
        output = OUTPUT.format(id=DECK_ID[options['first_language']])
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
        name = (
            'Eleri ' +
            options["first_language"] +
            '-' +
            options["second_language"]
        )
        deck = Deck(
            deck_id=DECK_ID[options['first_language']],
            name=name,
        )
        count = 0
        for word in Word.objects.filter(
            language=options['first_language'],
            sentence__translations__language=options['second_language'],
        ).order_by('-frequency', '-lemma__frequency'):
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
        Package(deck).write_to_file(output)
        self.stdout.write(
            self.style.SUCCESS(f"Exported {count} notes to {output}")
        )
