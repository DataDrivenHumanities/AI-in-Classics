# import
import numpy as np
import pandas as pd
from src.app.translate import Translator
from transformers import pipeline

# encodeing must = utf8
f = open("GreekList.txt", "r", encoding="utf8")
source = f.readlines()
f.close()

# remove /n from strings
for index, item in enumerate(source):
    source[index] = item.strip()

# initialize class
translator = Translator()
# call googltranlate for each entry in lines
translated = translator.translate(source, src="el", dest="en")

# print
"""
for t in translated:
    print(f'{t.origin} -> {t.text}')
"""

sentiment_task = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
    tokenizer="cardiffnlp/twitter-roberta-base-sentiment-latest",
)
for t in translated:
    print(f"{t.origin}  ->  {t.text}  ->    {sentiment_task(t.text)}\n")
