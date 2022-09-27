#import
from googletrans import Translator
from transformers import pipeline
import unicodedata

#encodeing must = utf8
f= open('GreekList.txt', 'r',encoding='utf8') 
source = f.readlines()
f.close()

#remove /n from strings
for index,item in enumerate(source): 
    source[index]=item.strip()

def strip_accents_and_lowercase(s):
   return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn').lower()
def remove_hyphens(s):
    return s.replace('-', '')
    
preprocessed=[None]*len(source)
for index,item in enumerate(source): 
    preprocessed[index]=  remove_hyphens(strip_accents_and_lowercase(item))

print(preprocessed)

#initialize class
translator = Translator()
#call googltranlate for each entry in lines
translated = translator.translate(preprocessed,src='el',dest='en')

#print 
'''
for t in translated:
    print(f'{t.origin} -> {t.text}')
'''

sentiment_task = pipeline("sentiment-analysis", model='cardiffnlp/twitter-roberta-base-sentiment-latest', 
tokenizer='cardiffnlp/twitter-roberta-base-sentiment-latest',device = 0)
for t in translated:
    print(f'{t.origin}  ->  {t.text}  ->    {sentiment_task(t.text)}\n')