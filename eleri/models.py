'''
Eleri data models for managing linguistic information.

This module defines models for storing and organizing multilingual lexical
data. The models provide a comprehensive structure for managing languages,
word meanings, canonical word forms, word frequencies, sentences, and their
translations.

The models are designed to maintain referential integrity through foreign key
relationships and enforce uniqueness constraints to prevent data duplication.

Models:
    Sense: Represents word meanings or definitions.
    Lemma: Represents canonical forms of words in specific languages.
    Word: Represents actual word forms in languages with frequency tracking.
    Sentence: Represents sentences in specific languages with word and
    translation mappings.
'''

from django.conf import settings
from django.db import models


class Sense(models.Model):
    '''
    Represents a sense or meaning of a word.

    Attributes:
        text (TextField): The textual description or definition of the sense,
        e.g. a word's meaning or definition.
    '''

    text = models.TextField()


class Lemma(models.Model):
    '''
    Represents a lexical lemma in a specific language.

    A lemma is a unique combination of a language, headword, and optionally a
    sense. It serves as an entry point in a lexicon and provides a referential
    integrity with the Language and Sense models.

    Attributes:
        headword (CharField): The canonical form of the word.
        language (ForeignKey): Reference to the Language model this lemma
        belongs to.
        sense (ForeignKey): Optional reference to the Sense model representing
        the meaning of this lemma.

    Constraints:
        - The combination of language, headword, and sense must be unique.
    '''

    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
    )
    headword = models.CharField(max_length=100)
    sense = models.ForeignKey(
        to=Sense,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f'({self.language}) {self.headword}'

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('language', 'headword', 'sense'),
                name='unique_lemma',
            ),
        )


class Word(models.Model):
    '''
    A word in a specific language, tracking its frequency and optionally its
    lemma.

    Attributes:
        language (ForeignKey): The language this word belongs to.
        form (CharField): The written form of the word.
        frequency (FloatField, optional): The frequency score or count of the
        word's usage.
        lemma (ForeignKey, optional): The base word this word derives from.

    Constraints:
        - A unique combination of language, form, and lemma.
        - A unique combination of language, form (without a lemma).
        - If the related lemma is deleted, the lemma reference is set to NULL (SET_NULL).
    '''

    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        db_index=True,
    )
    form = models.CharField(max_length=100)
    frequency = models.FloatField(
        null=True,
        blank=True,
        db_index=True,
    )
    lemma = models.ForeignKey(
        to=Lemma,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f'({self.language}) {self.form}'

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('language', 'form', 'lemma'),
                name='unique_word',
            ),
            models.UniqueConstraint(
                fields=('language', 'form'),
                condition=models.Q(lemma__isnull=True),
                name='unique_word_without_lemma',
            ),
        )

class Sentence(models.Model):
    '''
    Represents a sentence in a specific language.

    Attributes:
        language (CharField): The language of the sentence.
        text (TextField): The full text content of the sentence.
        words (ManyToManyField): Many-to-many relationship with Word model,
            representing individual words contained in this sentence.
        translation (ManyToManyField): Self-referential many-to-many
            relationship for linking sentences that are translations of each
            other.

    Constraints:
        - The combination of language and text must be unique.
    '''

    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
    )
    text = models.TextField()
    words = models.ManyToManyField(to=Word, blank=True)
    translation = models.ManyToManyField(to='self', blank=True)

    def __str__(self):
        return f'({self.language}) {self.text[:50]}...'

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('language', 'text'),
                name='unique_sentence',
            ),
        )