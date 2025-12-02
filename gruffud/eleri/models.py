'''
Django models for the Eleri app.

This module defines the database schema for a multilingual dictionary and
phrasebook. It supports multiple source and target languages, and captures the
following entities:

- Language: ISO code and human-readable name for supported languages.
- Word: Individual word forms tied to a language, with frequency counts.
- TranslationVariant: Links between source words and their possible target word
  translations.
- Phrase: Sample phrases tied to a language.
- PhraseTranslation: Links between source phrases
  and their translated equivalents.

The design emphasizes modularity and reusability:
- Languages are stored as independent records, allowing expansion.
- Words can be linked to multiple translations and sample phrases.
- Phrases are paired with translated phrases for contextual examples.

These models form the foundation for building a flexible multilingual lexicon,
supporting both word-level and phrase-level translation data.
'''

from django.conf import settings
from django.db import models


class Language(models.Model):
    '''
    Represents a natural language supported by the dictionary.

    Each Language record stores a short ISO 639-1 code (e.g., 'fi' for Finnish,
    'ru' for Russian) and a human-readable name. Words and phrases reference
    this model to indicate the language they belong to, ensuring consistency
    across translations.

    This model provides the foundation for linking source and target languages
    in word-level and phrase-level translation mappings.
    '''
    code = models.CharField(
        max_length=10,
        unique=True,
        choices=settings.LANGUAGES,
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Word(models.Model):
    '''
    Represents a word form in a specific language.

    Each Word record stores:
    - The language it belongs to (via ForeignKey to Language).
    - The actual word form (inflected or variant).
    - A frequency value indicating how often this form occurs in a corpus.

    Words can be linked to:
    - TranslationVariant records, which connect source words to target words.
    - Sample phrases, providing contextual usage examples.

    This model supports both raw frequency counts and normalized values,
    enabling analysis of word usage across languages.
    '''
    language = models.ForeignKey(
        to=Language,
        on_delete=models.CASCADE,
    )
    form = models.CharField(max_length=100)
    frequency = models.DecimalField(
        max_digits=20,
        decimal_places=15,
        default=0,
    )

    def __str__(self):
        return f'{self.form} ({self.language.code})'

    class Meta:
        unique_together = (
            'language',
            'form',
        )
        indexes = [models.Index(fields=['frequency'])]

class TranslationVariant(models.Model):
    '''
    Represents a translation link between two word forms.

    Each TranslationVariant connects:
    - A source word (in the source language).
    - A target word (in the target language).

    This model allows multiple translation variants for a single source word,
    reflecting the fact that words often have more than one possible equivalent
    in another language. It also supports reverse lookups, so you can query
    which source words map to a given target word.

    Example:
        Finnish word 'kissa' (cat) → Russian word 'кошка'
        Finnish word 'kissa' (cat) → Russian word 'кот'
    '''
    source_word = models.ForeignKey(
        to=Word,
        on_delete=models.CASCADE,
    )
    target_word = models.ForeignKey(
        to=Word,
        on_delete=models.CASCADE,
        related_name='target_translationvariant_set',
    )

    def __str__(self):
        return f'{self.source_word} → {self.target_word}'

    class Meta:
        unique_together = (
            'source_word',
            'target_word',
        )

class Phrase(models.Model):
    '''
    Represents a sample phrase in a specific language.

    Each Phrase record stores:
    - The language it belongs to (via ForeignKey to Language).
    - The phrase text itself.

    Phrases provide contextual examples of word usage and can be linked to
    translated phrases through the PhraseTranslation model. They may also be
    associated with individual words to illustrate how those words appear in
    natural language contexts.

    Example:
        Finnish phrase: 'Minulla on kissa.'
        Russian phrase: 'У меня есть кошка.'
    '''
    language = models.ForeignKey(
        to=Language,
        on_delete=models.CASCADE,
    )
    text = models.TextField()
    words = models.ManyToManyField(Word)

    def __str__(self):
        return f'{self.text[:50]}...'


class PhraseTranslation(models.Model):
    '''
    Represents a translation link between two phrases.

    Each PhraseTranslation connects:
    - A source phrase (in the source language).
    - A target phrase (in the target language).

    This model allows you to store parallel phrase pairs, providing contextual
    examples of how words and expressions are used across languages. It supports
    multiple translations for a single source phrase, reflecting natural variation
    in phrasing and usage.

    Example:
        Source phrase (Finnish): 'Minulla on kissa.'
        Target phrase (Russian): 'У меня есть кошка.'
    '''
    source_phrase = models.ForeignKey(
        to=Phrase,
        on_delete=models.CASCADE,
    )
    target_phrase = models.ForeignKey(
        to=Phrase,
        on_delete=models.CASCADE,
        related_name='target_phrasetranslation_set',
    )

    def __str__(self):
        return f'{self.source_phrase} → {self.target_phrase}'

    class Meta:
        unique_together = (
            'source_phrase',
            'target_phrase',
        )