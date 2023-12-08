import csv
from flask import Flask, render_template, request, redirect, url_for
from io import StringIO
import time

import pandas as pd
from sqlalchemy import create_engine

from sqlalchemy import text
import csv
from io import StringIO
from pandasql import sqldf
import time
import pandas as pd

dataname = 'preliminaryWords.csv'
dataframe = pd.read_csv(dataname)

def find_author(name):
    #SQL query gathering all of the information for a specific author
    #Input is limited by 5, but will change upon further testing
    sql = f'''
        SELECT *
        FROM dataframe
        WHERE author = '{name}'
        LIMIT 10;
    '''

    return sqldf(sql)

def find_word(word):
    #SQL query gathering all of the information for a specific word
    sql = f'''
        SELECT *
        FROM dataframe
        WHERE aspect = '{word}' AND aspect IS NOT NULL
        LIMIT 10;
    '''

    return sqldf(sql)

def avg_sentiment(author = 'all'):
    #Gathers the average sentiment for a word where it appears everywhere (for all authors)
    if author == 'all':
        sql = f'''
            SELECT aspect, COUNT(aspect) AS num_words, AVG(confidence) as avg_sentiment
            FROM dataframe
            WHERE aspect IS NOT NULL AND aspect NOT Like '%%[^0-9]%%'
            GROUP BY aspect
            ORDER BY num_words DESC;
        '''
    #Gathers the average sentiment for a word where it appears within a specific author's text (each author uses different syntax)
    else:
        sql = f'''
            SELECT author, aspect, COUNT(aspect) as num_words, AVG(confidence) as avg_sentiment
            FROM dataframe
            WHERE author = '{author}' AND aspect IS NOT NULL
            GROUP BY aspect, author
            ORDER BY num_words DESC;
        '''

    # Return SQL query as a pandas dataframe
    return sqldf(sql)


def books_per_author():
    #Helpful statistic when comparing who wrote the most books and which words can appear most
    sql = f'''
        SELECT author, COUNT(author) AS num_books, COUNT(aspect) AS num_words
        FROM dataframe
        GROUP BY author
        ORDER BY num_books DESC, num_words DESC
    '''

    # Return SQL query as a pandas dataframe
    return sqldf(sql)

def highest_words(author):
    #Counts the number of words to see which appear the most (specific or all)
    if author == 'all':
        sql = f'''
            SELECT aspect, COUNT(aspect) AS num_words
            FROM dataframe
            WHERE aspect IS NOT NULL AND aspect NOT Like '%%[^0-9]%%'
            GROUP BY aspect
            ORDER BY num_words DESC
        '''
    else:
        sql = f'''
            SELECT author, aspect, COUNT(aspect) AS num_words
            FROM dataframe
            WHERE author = '{author}' AND aspect IS NOT NULL AND aspect NOT Like '%%[^0-9]%%'
            GROUP BY aspect, author
            ORDER BY num_words DESC
        '''

    # Return SQL query as a pandas dataframe
    return sqldf(sql)

def words_per_book(book, group = 'num_words'):

    if group == 'num_words':

        sql = f'''
            SELECT aspect, COUNT(aspect) AS num_words, AVG(confidence) AS avg_sentiment
            FROM dataframe
            WHERE aspect IS NOT NULL AND title = '{book}'
            GROUP BY aspect, title
            ORDER BY num_words DESC
        '''
    else:
        sql = f'''
            SELECT aspect, COUNT(aspect) AS num_words, AVG(confidence) AS avg_sentiment
            FROM dataframe
            WHERE aspect IS NOT NULL AND title = '{book}'
            GROUP BY aspect, title
            ORDER BY avg_sentiment DESC
        '''

    return sqldf(sql)

def find_similar(specific, limit):
    sql = f'''
        SELECT *
        FROM dataframe
        WHERE aspect LIKE '%%{specific}%%' AND aspect IS NOT NULL
        LIMIT '{limit}';
    '''
    return sqldf(sql)

def find(word, limit):
  return find_similar(word, limit).to_markdown()


app = Flask(__name__)

#Load dataset
#csv_df = pd.read_csv('0-9999_edited.csv')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        #get the search criteria for each of the dropdowns
        search_criteria = request.form.get('search_criteria')
        search_term_author = request.form.get('search_term_author')
        search_term_word = request.form.get('search_term_word')
        search_term_sentiment = request.form.get('search_term_sentiment')
        search_term_highest = request.form.get('search_term_highest')
        search_term_wordsbook = request.form.get('search_term_wordsbook')

        #call each function depending on what user selected
        if search_criteria == 'author':
            data = find_author(search_term_author)
            columns_to_display = ["Section ID", "Text Section", "Title", "Author", "Translated Text", "TreePath", "aspect", "confidence"]
            data_to_display = data[columns_to_display]

        elif search_criteria == 'word':
            data = find_word(search_term_word)
            columns_to_display = ["Section ID", "Text Section", "Title", "Author", "Translated Text", "TreePath", "aspect", "confidence"]
            data_to_display = data[columns_to_display]

        elif search_criteria == 'books_per_author':
            data_to_display = books_per_author()

        elif search_criteria == 'avg_sentiment':
            data_to_display = avg_sentiment(search_term_sentiment)

        elif search_criteria == 'highest_words':
            data_to_display = highest_words(search_term_highest)

        elif search_criteria == 'words_per_book':
            data_to_display = words_per_book(search_term_wordsbook)

        else:
            data = []

        return render_template('display.html', data=data_to_display.to_html(classes='dataframe'))

    return render_template('dashboard.html')

    # if request.method == "POST": 
    #     author_name = request.form.get('author_name')
    #     data = find_author(author_name)
    #     #return render_template('display.html', data=data.to_html(classes='dataframe'))
    
    #     word = request.form.get('word')
    #     data = find_word(word)
    #     return render_template('display.html', data=data.to_html(classes='dataframe'))

    
    # return render_template('dashboard.html')


if __name__ == '__main__':
    app.run(debug=True)