from cltk.lemmatize import GreekBackoffLemmatizer
from cltk.languages.utils import get_lang
from cltk.alphabet.grc import normalize_grc, filter_non_greek


class GreekCLTKLemmatizer:
    """Greek lemmatizer using CLTK package"""

    def __init__(self):
        """Initialize the Greek lemmatizer with dictionary files"""
        self.lemmatizer = GreekBackoffLemmatizer()
        self.lang = get_lang('grc')

    def lemmatize_text(self, text: str):
        filtered_text = filter_non_greek(text)
        normalized_text = normalize_grc(filtered_text)
        words = normalized_text.split()

        lemmas = self.lemmatizer.lemmatize(words)
        return [lemma for _, lemma in lemmas]