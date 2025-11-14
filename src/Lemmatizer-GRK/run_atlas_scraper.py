#!/usr/bin/env python3
"""
Run Atlas Lemmas and Conjugations Scraper
Standalone script version of Atlas_Lemmas_Conjugations_Scraper.ipynb
"""

import csv
import json
import sys
import time
import re
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ATLAS_BASE = "https://atlas.perseus.tufts.edu"
LEMMA_LIST_URL = f"{ATLAS_BASE}/lemmas/?lang=grc"

HEADERS = {
    'User-Agent': 'AI-in-Classics Atlas Scraper (+https://github.com/DataDrivenHumanities/AI-in-Classics)'
}

@dataclass
class Lemma:
    lemma: str
    atlas_id: str
    url: str
    source: str = 'Atlas'
    language: str = 'grc'

@dataclass
class InflectedForm:
    lemma: str
    atlas_id: str
    inflected_form: str
    morphology: Optional[str] = None
    frequency: Optional[int] = None


def fetch(url: str, session: requests.Session, timeout: int = 30) -> str:
    """Fetch URL with error handling."""
    r = session.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def to_abs(href: str) -> str:
    """Convert relative URL to absolute."""
    if href.startswith('http'):
        return href
    return urljoin(ATLAS_BASE, href)


def scrape_lemma_list_page(page_num: int, session: requests.Session) -> List[Lemma]:
    """Scrape lemmas from a single page of the Atlas."""
    url = f"{LEMMA_LIST_URL}&page={page_num}"
    print(f'Fetching page {page_num}: {url}')
    
    html = fetch(url, session)
    soup = BeautifulSoup(html, 'html.parser')
    
    lemmas = []
    
    for link in soup.find_all('a', href=re.compile(r'/lemma/\d+/')):
        lemma_text = link.get_text(strip=True)
        
        if lemma_text in ['start', 'prev', 'next', 'end', '[', ']'] or not lemma_text:
            continue
        
        href = link['href']
        match = re.search(r'/lemma/(\d+)/', href)
        if not match:
            continue
        
        atlas_id = match.group(1)
        lemma_url = to_abs(href)
        
        lemmas.append(Lemma(
            lemma=lemma_text,
            atlas_id=atlas_id,
            url=lemma_url
        ))
    
    return lemmas


def scrape_lemma_inflections(lemma: Lemma, session: requests.Session) -> List[InflectedForm]:
    """Scrape inflected forms from an individual lemma page."""
    try:
        html = fetch(lemma.url, session)
        soup = BeautifulSoup(html, 'html.parser')
        
        inflections = []
        seen_forms = set()  # Avoid duplicates
        
        # Look for links to form pages (format: /form/NUMBER/)
        # These contain the inflected forms
        for link in soup.find_all('a', href=re.compile(r'/form/\d+/')):
            form_text = link.get_text(strip=True)
            
            # Clean up the form text (remove brackets, special chars from OCR errors)
            form_text = re.sub(r'[<>[\]{}]', '', form_text)
            form_text = form_text.strip()
            
            # Skip if empty, same as lemma, or already seen
            if not form_text or form_text == lemma.lemma or form_text in seen_forms:
                continue
            
            # Skip if it's just punctuation or numbers
            if re.match(r'^[.,;:·\[\]\d\s]+$', form_text):
                continue
            
            # Skip very short non-Greek forms (OCR errors)
            if len(form_text) <= 2 and not re.search(r'[α-ωΑ-Ω]', form_text):
                continue
            
            seen_forms.add(form_text)
            
            # Try to find morphological info nearby (in parent or sibling elements)
            morph_info = None
            parent = link.find_parent(['td', 'div', 'li'])
            if parent:
                # Look for morphology tags or description
                morph_tag = parent.find(['span', 'small'], class_=re.compile(r'morph|parse|grammar'))
                if morph_tag:
                    morph_info = morph_tag.get_text(strip=True)
            
            inflections.append(InflectedForm(
                lemma=lemma.lemma,
                atlas_id=lemma.atlas_id,
                inflected_form=form_text,
                morphology=morph_info
            ))
        
        return inflections
    
    except Exception as e:
        print(f'ERROR scraping inflections for {lemma.lemma}: {e}', file=sys.stderr)
        return []


def write_lemmas_csv(path: str, items: List[Lemma]) -> None:
    """Write lemmas to CSV."""
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['language', 'source', 'lemma', 'atlas_id', 'url'])
        for it in items:
            w.writerow([it.language, it.source, it.lemma, it.atlas_id, it.url])


def write_inflections_csv(path: str, items: List[InflectedForm]) -> None:
    """Write inflected forms to CSV."""
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['lemma', 'atlas_id', 'inflected_form', 'morphology', 'frequency'])
        for it in items:
            w.writerow([it.lemma, it.atlas_id, it.inflected_form, it.morphology or '', it.frequency or ''])


def main():
    """Run the scraper."""
    print("="*70)
    print("PERSEUS ATLAS LEMMAS AND CONJUGATIONS SCRAPER")
    print("="*70)
    
    # Configuration
    START_PAGE = 1
    NUM_PAGES = 5  # Start with 5 pages for testing
    DELAY = 0.5
    SAMPLE_SIZE = 10  # Only scrape inflections for first 10 lemmas
    INFLECTION_DELAY = 1.0
    
    session = requests.Session()
    
    # Step 1: Scrape lemma lists
    print(f"\nStep 1: Scraping lemma lists (pages {START_PAGE}-{START_PAGE + NUM_PAGES - 1})")
    print("-"*70)
    
    all_lemmas = []
    for page in range(START_PAGE, START_PAGE + NUM_PAGES):
        try:
            lemmas = scrape_lemma_list_page(page, session)
            all_lemmas.extend(lemmas)
            print(f'  -> Collected {len(lemmas)} lemmas (total: {len(all_lemmas)})')
            time.sleep(DELAY)
        except Exception as e:
            print(f'ERROR on page {page}: {e}', file=sys.stderr)
    
    print(f'\nTotal lemmas collected: {len(all_lemmas)}')
    
    if not all_lemmas:
        print("No lemmas collected. Exiting.")
        return 1
    
    # Preview
    print(f'\nFirst 10 lemmas:')
    for lemma in all_lemmas[:10]:
        print(f'  {lemma.lemma} (ID: {lemma.atlas_id})')
    
    # Step 2: Scrape inflections
    print(f"\nStep 2: Scraping inflections for {SAMPLE_SIZE} lemmas")
    print("-"*70)
    
    all_inflections = []
    sample_lemmas = all_lemmas[:SAMPLE_SIZE]
    
    for i, lemma in enumerate(sample_lemmas, 1):
        print(f'[{i}/{len(sample_lemmas)}] Scraping inflections for: {lemma.lemma}')
        
        inflections = scrape_lemma_inflections(lemma, session)
        all_inflections.extend(inflections)
        
        print(f'  -> Found {len(inflections)} inflected forms')
        time.sleep(INFLECTION_DELAY)
    
    print(f'\nTotal inflected forms collected: {len(all_inflections)}')
    
    # Step 3: Save results
    print(f"\nStep 3: Saving results")
    print("-"*70)
    
    LEMMAS_CSV = 'database/atlas_lemmas.csv'
    LEMMAS_JSON = 'database/atlas_lemmas.json'
    
    write_lemmas_csv(LEMMAS_CSV, all_lemmas)
    print(f'✓ Wrote {len(all_lemmas)} lemmas to {LEMMAS_CSV}')
    
    with open(LEMMAS_JSON, 'w', encoding='utf-8') as f:
        json.dump([asdict(l) for l in all_lemmas], f, ensure_ascii=False, indent=2)
    print(f'✓ Wrote {len(all_lemmas)} lemmas to {LEMMAS_JSON}')
    
    if all_inflections:
        INFLECTIONS_CSV = 'database/atlas_inflections.csv'
        INFLECTIONS_JSON = 'database/atlas_inflections.json'
        
        write_inflections_csv(INFLECTIONS_CSV, all_inflections)
        print(f'✓ Wrote {len(all_inflections)} inflected forms to {INFLECTIONS_CSV}')
        
        with open(INFLECTIONS_JSON, 'w', encoding='utf-8') as f:
            json.dump([asdict(i) for i in all_inflections], f, ensure_ascii=False, indent=2)
        print(f'✓ Wrote {len(all_inflections)} inflected forms to {INFLECTIONS_JSON}')
    
    # Summary
    print("\n" + "="*70)
    print("SCRAPING SUMMARY")
    print("="*70)
    print(f'Pages scraped: {NUM_PAGES}')
    print(f'Total lemmas collected: {len(all_lemmas)}')
    print(f'Lemmas with inflections checked: {len(sample_lemmas)}')
    print(f'Total inflected forms found: {len(all_inflections)}')
    if all_inflections:
        print(f'Average forms per lemma: {len(all_inflections) / len(sample_lemmas):.1f}')
    print('='*70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
