from deep_translator import GoogleTranslator


def translate(text: str, src: str = "auto", dest: str = "en") -> str:
    """
    If you need to use google translator
    """
    return GoogleTranslator(source=src, target=dest).translate(text)
