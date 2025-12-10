'''
This command generates an initial set of sentences for a language pair.

It uses the Words in the first language (ordered by frequency) to generate
sentences (with linked words), translating them into the second language.

It processes words in batches, bulk creating the sentences and their
translations.

Example usage:

    manage.py initial_sentences fi ru

This will generate sentences for the Finnish-Russian language pair.
'''

from json import loads
from django.db import transaction
from django.conf import settings
from django.core.management.base import BaseCommand
from openai import OpenAI
from eleri.models import Sentence, Word


SYSTEM_PROMPT = '''
    You will receive a list of {first_language} word forms. With each form
    generate a natural {first_language} sentence containing that exact form and
    translated {second_language} sentence. Return a JSON object by the
    following template:
    {{
        form: {{
                "original_sentence": str,
                "translated_sentence": str
        }},
        ...
    }}
'''
BATCH = 100


class Command(BaseCommand):
    help = 'Generate initial sentences'

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
        languages = dict(settings.LANGUAGES)
        words = Word.objects.filter(
            language=options['first_language'],
            sentence__isnull=True,
        ).order_by('-frequency')
        if words.count() == 0:
            self.stdout.write(
                self.style.WARNING('No words to generate sentences for')
            )
            return
        client = OpenAI(base_url=settings.OPENAI_API_BASE_URL)
        count = words.count()
        batch_size = BATCH if BATCH else count
        for index in range(0, count, batch_size):
            self.stdout.write(f'Generating batch of {batch_size} from {index}.')
            words_batch = words[index:index + batch_size]
            data = loads(
                client.chat.completions.create(
                    model=settings.OPENAI_API_MODEL,
                    messages=[
                        {
                            'role': 'system',
                            'content': SYSTEM_PROMPT.format(
                                first_language=languages[
                                    options['first_language']
                                ],
                                second_language=languages[
                                    options['second_language']
                                ],
                            ),
                        },
                        {
                            'role': 'user',
                            'content': '\n'.join(
                                [word.form for word in words_batch]
                            ),
                        },
                    ],
                ).choices[0].message.content
            )
            sentences = []
            translations = []
            for word in words_batch:
                sentence = Sentence(
                    language=options['first_language'],
                    text=data[word.form]['original_sentence'],
                )
                translation = Sentence(
                    language=options['second_language'],
                    text=data[word.form]['translated_sentence'],
                )
                sentences.append(sentence)
                translations.append(translation)
            with transaction.atomic():
                Sentence.objects.bulk_create(sentences + translations)
                sentence_word = Sentence.words.through
                sentence_word.objects.bulk_create(
                    (
                        sentence_word(
                            sentence=sentence,
                            word=word,
                        )
                        for sentence, word in zip(sentences, words_batch)
                    )
                )
                sentence_translation = Sentence.translation.through
                sentence_translation.objects.bulk_create(
                    (
                        sentence_translation(
                            from_sentence=sentence,
                            to_sentence=translation,
                        )
                        for sentence, translation
                        in zip(sentences, translations)
                    )
                )
                sentence_translation.objects.bulk_create(
                    (
                        sentence_translation(
                            from_sentence=translation,
                            to_sentence=sentence,
                        )
                        for sentence, translation
                        in zip(sentences, translations)
                    )
                )