from cltk.lemmatize import GreekBackoffLemmatizer
from cltk.languages.utils import get_lang
from cltk.alphabet.grc import normalize_grc, filter_non_greek
from cltk.sentence.grc import GreekRegexSentenceTokenizer
import typing

def print_util(variable, count):
    if count < 2:
        print(variable)
    return 2

class GreekCLTKLemmatizer:
    """Greek lemmatizer using CLTK package"""

    def __init__(self):
        """Initialize the Greek lemmatizer with dictionary files"""
        self.lemmatizer = GreekBackoffLemmatizer()
        self.lang = get_lang('grc')

    def lemmatize_text(self, text: str) -> list[str]:
        splitter = GreekRegexSentenceTokenizer()
        sentence_tokens = splitter.tokenize(text)

        sentence_lists = []
        for token in sentence_tokens:  # iterate through list of sentences
            filtered_text = filter_non_greek(token)
            normalized_text = (normalize_grc(filtered_text))
            sentence_lists.append(normalized_text.split())

        lemma_list = []
        for split_sentence in sentence_lists:
            lemmas = self.lemmatizer.lemmatize(split_sentence)
            lemma_str = " ".join([lemma for _, lemma in lemmas])
            lemma_list.append(lemma_str)
        return lemma_list