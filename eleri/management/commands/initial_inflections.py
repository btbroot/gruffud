'''
This command generates an initial set of inflections for a language.

It uses the Lemma in the (ordered by frequency) to generate
inflection Words (with linked Lemmas) and saves them as Word.form.

It processes Lemmas in batches, bulk creating the Words.

Example usage:

    manage.py initial_inflections en

This will generate inflections for English language.
'''

from json import JSONDecodeError, loads
from django.db import transaction
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openai import APIStatusError, InternalServerError, OpenAI, RateLimitError
from eleri.models import Lemma, Word


SYSTEM_PROMPT = '''
    You will receive a list of {language} headwords. With each headword
    generate all common inflections. Return a JSON object by the
    following template:
    {{
        headword: [
                inflection1,
                inflection2,
                ...
        ],
        ...
    }}
'''
BATCH_SIZE = 100
USER_ERROR = 2


class Command(BaseCommand):
    help = 'Generate initial inflections'

    def add_arguments(self, parser):
        parser.add_argument(
            'language',
            type=str,
            help='Language code of the dictionary words',
        )

    def handle(self, *args, **options):
        languages = dict(settings.LANGUAGES)
        lemmas = Lemma.objects.filter(
            language=options['language'],
            word__isnull=True,
        ).order_by('-frequency')
        count = lemmas.count()
        if count == 0:
            self.stdout.write(
                self.style.WARNING('No lemmas to generate inflections for')
            )
            return
        client = OpenAI(base_url=settings.OPENAI_API_BASE_URL)
        batch_size = BATCH_SIZE if BATCH_SIZE else count
        for index in range(0, count, batch_size):
            self.stdout.write(f'Generating batch of {batch_size} from {index}.')
            lemmas_batch = lemmas[index:index + batch_size]
            while ...:
                try:
                    resp = client.chat.completions.create(
                        model=settings.OPENAI_API_MODEL,
                        messages=[
                            {
                                'role': 'system',
                                'content': SYSTEM_PROMPT.format(
                                    language=languages[options['language']]
                                ),
                            },
                            {
                                'role': 'user',
                                'content': str([
                                    lemma.headword for lemma in lemmas_batch
                                ]),
                            },
                        ],
                    )
                except (RateLimitError, APIStatusError) as exception:
                    raise CommandError(str(exception), returncode=USER_ERROR)
                except InternalServerError as exception:
                    self.stdout.write(self.style.ERROR(str(exception)))
                    continue
                break
            content = (
                resp.choices[0].message.content.strip('```json').strip('```')
            )
            try:
                data = loads(content)
            except JSONDecodeError as exception:
                raise CommandError(f'Could not parse response: {content}')
            for lemma in lemmas_batch:
                if lemma.headword not in data:
                    self.stdout.write(
                        self.style.WARNING(f'No data for {lemma.headword}')
                    )
                    continue
                self.stdout.write(f'Creating inflections for {lemma.headword}')
                with transaction.atomic():
                    for word in data[lemma.headword]:
                        word, created = (
                            Word.objects.get_or_create(
                                language=options['language'],
                                form=word,
                                lemma=lemma,
                                source=settings.OPENAI_API_MODEL,
                            )
                        )
