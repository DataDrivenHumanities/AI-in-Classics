import asyncio
import aiohttp
from aiohttp import ClientResponseError, ClientConnectorError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urljoin
from pathlib import Path
import csv
import re
import unicodedata
import argparse
import random

BASE_URL = "https://atlas.perseus.tufts.edu"
INDEX_URL = BASE_URL + "/lemmas/?lang=grc&page={pg}"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DDHBot/1.0)"}

# text helpers
def clean_perseus_cell(text):
    '''Removes the frequency from the lemmas'''
    if not text:
        return ""
    parts = text.split()
    valid_parts = [p for p in parts if not re.match(r'^[\d,]+$', p)]
    return " ".join(valid_parts)

def slugify_lemma(lemma_text: str) -> str:
    '''converts lemma to clean filename'''
    # uses NFD to split characters
    nfkd = unicodedata.normalize('NFD', lemma_text)
    # removes accents, etc. 
    no_accents = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # replace everything that's not greek/english/number with underscores
    slug = re.sub(r'[^a-z0-9α-ω]', '_', no_accents.lower())
    return re.sub(r'_+', '_', slug).strip('_')


# parsing logic
def parse_index_for_urls(html_text):
    """
    Scrapes list page to find URLs for the details.
    Returns a list for full URLs to the pages.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    urls = []
    # finds the first table tag
    table = soup.find('table')
    if not table:
        return []
    # finds the table body in the table
    tbody = table.find('tbody')
    if not tbody:
        return []
    # loops through every row in table
    for tr in tbody.find_all('tr'):
        # finds first column of row, checks if word for row has a url
        td = tr.find('td')
        if td:
            a = td.find('a')
            if a and 'href' in a.attrs:
                full_url = urljoin(BASE_URL, a['href'])
                urls.append(full_url)
    return urls

def parse_flexion_tables(html_text, page_url):
    """
    Scrapes the details page for paradigm forms using the Forms List.
    Returns (lemma_text, list_of_rows)
    """
    soup = BeautifulSoup(html_text)
    rows = []
    # extract lemma header
    header = soup.find('h1') or soup.find('h2')
    raw_lemma_text = header.get_text(strip=True) if header else "unknown_lemma"
    lemma_text = raw_lemma_text.replace("Lemma:", "").split("(")[0].strip()
    # find Forms List table
    target_table = None
    for table in soup.find_all('table'):
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        if "form" in headers or "parse" in headers:
            target_table = table
            break
    # if Forms List table doesn't exist for some reason? may need to add error message too.
    if not target_table:
        return lemma_text, []
    tbody = target_table.find('tbody') or target_table
    # loops through all table rows
    for tr in tbody.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) < 2:
            continue
        # grabs Greek word and code
        raw_form = tds[0].get_text(" ", strip=True)
        form_val = clean_perseus_cell(raw_form)
        parse_string = tds[1].get_text(strip=True)
        pos = ""
        person = ""
        number = ""
        tense = ""
        mood = ""
        voice = ""
        gender = ""
        case = ""
        # splits code and classifies according to value.
        parts = parse_string.split()
        for part in parts:
            subparts = part.split('.')
            for tag in subparts:
                tag = tag.upper()
                if tag in ['NOM', 'GEN', 'DAT', 'ACC', 'VOC']: case = tag
                elif tag in ['SG', 'PL', 'DU']: number = tag
                elif tag in ['MASC', 'FEM', 'NEUT']: gender = tag
                elif tag in ['1ST', '2ND', '3RD']: person = tag
                elif tag in ['PRES', 'IMPF', 'FUT', 'AOR', 'PERF', 'PLUP']: tense = tag
                elif tag in ['IND', 'SUBJ', 'OPT', 'IMPERAT', 'INF', 'PTCP']: mood = tag
                elif tag in ['ACT', 'MID', 'PASS', 'MP']: voice = tag
        rows.append({
            "lemma_text": lemma_text,
            "form": form_val,
            "pos": pos,
            "case": case,
            "number": number,
            "gender": gender,
            "person": person,
            "tense": tense,
            "mood": mood,
            "voice": voice,
            "page_url": page_url,
            "raw_parse": parse_string
        })
    return lemma_text, rows