
import multiprocessing as mp
from pprint import pprint
from typing import Iterable, Union

import cltk
from cltk import NLP
from cltk.languages.pipelines import LatinPipeline
from cltk.tokenizers.line import LineTokenizer
from termcolor import colored, cprint

# NLP document analysis demo
# text
vitruvius = "Architecti est scientia pluribus disciplinis et variis eruditionibus ornata, quae ab ceteris artibus perficiuntur. Opera ea nascitur et fabrica et ratiocinatione."

# cltk.nlp.NLP object
cltk_nlp = NLP(language='lat') 

# region
cprint(text='cltk.nlp.NLP object:', 
       color='green', 
       attrs=list(['bold', 'dark'])))
cprint(text=cltk_nlp, color='green')

# process text into Doc object for further analysis
cltk_doc = cltk_nlp.analyze(text=vitruvius)
cprint(text='-' * 100, color='green')
cprint(text='Doc object:', color='green')
cprint(text='-' * 100, color='green')
cprint(text=cltk_doc, color='green')

# tokenization
tokens = cltk_doc.tokens[:5]
cprint(text='-' * 100, color='green')
cprint(text='tokens:', color='green')
cprint(text='-' * 100, color='green')
cprint(text=tokens, color='green')

raise Exception()

# lemmatization
lemmas = cltk_doc.lemmata[:5]
cprint(text='-' * 100, color='green')
pprint('lemmas:')
cprint(text='-' * 100, color='green')
pprint(lemmas)

# morphosyntactic features
morphos = cltk_doc.morphosyntactic_features[2]  # 'scientia'
cprint(text='-' * 100, color='green')
pprint('morphosyntactic features:')
cprint(text='-' * 100, color='green')
pprint(morphos)

# part-of-speech (POS) tagging
pos_tags = cltk_doc.pos[:5]
cprint(text='-' * 100, color='green')
pprint('POS tags:')
cprint(text='-' * 100, color='green')
pprint(pos_tags)

# sentence tokenization
sent_tokens = cltk_doc.sentences_tokens
cprint(text='-' * 100, color='green')
pprint('sentence tokens:')
cprint(text='-' * 100, color='green')
pprint(sent_tokens)

# analysis of a single word
word = cltk_doc.words[4]
cprint(text='-' * 100, color='green')
pprint(f'Word analysis for {word}:')
cprint(text='-' * 100, color='green')

pprint(word.pos)
pprint(word.category)
pprint(word.features)
pprint(word.dependency_relation)
pprint(word.governor)
pprint(word.string )
pprint(word.embedding)
pprint(word.index_sentence)
#endregion

# pipeline demo
#region
pipeline = LatinPipeline()
cprint(text='-' * 100, color='green')
pprint('Latin Pipeline')
cprint(text='-' * 100, color='green')
pprint('Description:')
cprint(text='-' * 100, color='green')
pprint(pipeline.description)
cprint(text='-' * 100, color='green')
pprint('Language settings and configuration:')
cprint(text='-' * 100, color='green')
pprint(pipeline.language)
cprint(text='-' * 100, color='green')
pprint('Language:')
cprint(text='-' * 100, color='green')
pprint(pipeline.language.name)
cprint(text='-' * 100, color='green')
pprint('Processes in pipeline:')
cprint(text='-' * 100, color='green')
pprint(pipeline.processes)
#endregion

def filter_by_lemma(doc: cltk.core.data_types.Doc, lemmas: Iterable[str]):
    """
    Filter terms by membership in a set of lemmas.

    Parameters:
        doc (cltk.core.data_types.Doc): NLP document.
        lemmas (Iterable[str]): Lemmas used to filter terms.

    Returns:
        Iterable[str]: Terms satsifying given lemmas.
    """
    lemmas = set(lemmas)
    lemmas_in_doc = doc.lemmata
    return list([token for idx, token in enumerate(iterable=doc.tokens) if lemmas_in_doc[idx] in lemmas])

def filter_by_pos(doc: cltk.core.data_types.Doc, pos_tags: Iterable[str]):
    """
    Filter terms by membership in a set of parts of speech (POS) tags.

    Parameters:
        doc (cltk.core.data_types.Doc): NLP document.
        pos_tags (Iterable[str]): Part of speech tags used to filter terms.

    Returns:
        Iterable[str]: Terms satsifying given part-of-speech tags.
    """
    pos_tags = set(pos_tags)
    return list([token for idx, pos_tag in enumerate(iterable=doc.pos_tags) if pos_tag in pos_tags])     

def filter_by_weight(terms: Iterable[str], weights: Iterable[int], threshold: Union[int, float]):
    """
    Filter terms that have a weight greater than given threshold.

    Parameters:
        terms (Iterable[str]): Terms to filter.
        weights (Iterable[int]): Weights of terms to filter.
        threshold (Union[int, float]): Minimum level that the weight of a term must exceed to continue consideration of th term.

    Returns:
        Iterable[str]: Terms satisfying the minimum threshold for weights.
    """
    if len(terms) != len(weights):
        raise ValueError(f'The number of terms ({len(terms)}) does not equal the number of weights ({len(weights)}).')

    return list([terms[idx] for idx in range(len(terms)) if weight[idx] > threshold])
