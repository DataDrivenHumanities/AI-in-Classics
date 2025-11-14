#!/usr/bin/env python3
"""
Run Atlas Lemmas and Conjugations Scraper - ASYNC BATCH VERSION
Uses concurrent requests to speed up scraping by 10-20x
"""

import asyncio
import csv
import json
import sys
import time
import re
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urljoin

import aiohttp
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


async def fetch_async(session: aiohttp.ClientSession, url: str, retry_count: int = 3) -> str:
    """Fetch URL asynchronously with retry logic."""
    for attempt in range(retry_count):
        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 2
                print(f'  -> Retry {url} in {wait_time}s (attempt {attempt + 1}/{retry_count})')
                await asyncio.sleep(wait_time)
            else:
                print(f'  -> Failed to fetch {url}: {e}', file=sys.stderr)
                raise


def to_abs(href: str) -> str:
    """Convert relative URL to absolute."""
    if href.startswith('http'):
        return href
    return urljoin(ATLAS_BASE, href)


async def scrape_lemma_list_page_async(session: aiohttp.ClientSession, page_num: int) -> List[Lemma]:
    """Scrape lemmas from a single page asynchronously."""
    url = f"{LEMMA_LIST_URL}&page={page_num}"
    
    try:
        html = await fetch_async(session, url)
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
    
    except Exception as e:
        print(f'ERROR on page {page_num}: {e}', file=sys.stderr)
        return []


async def scrape_lemma_inflections_async(session: aiohttp.ClientSession, lemma: Lemma) -> List[InflectedForm]:
    """Scrape inflected forms from an individual lemma page asynchronously."""
    try:
        html = await fetch_async(session, lemma.url)
        soup = BeautifulSoup(html, 'html.parser')
        
        inflections = []
        seen_forms = set()
        
        for link in soup.find_all('a', href=re.compile(r'/form/\d+/')):
            form_text = link.get_text(strip=True)
            
            # Clean up the form text
            form_text = re.sub(r'[<>[\]{}]', '', form_text)
            form_text = form_text.strip()
            
            # Skip if empty, same as lemma, or already seen
            if not form_text or form_text == lemma.lemma or form_text in seen_forms:
                continue
            
            # Skip if it's just punctuation or numbers
            if re.match(r'^[.,;:·\[\]\d\s]+$', form_text):
                continue
            
            # Skip very short non-Greek forms
            if len(form_text) <= 2 and not re.search(r'[α-ωΑ-Ω]', form_text):
                continue
            
            seen_forms.add(form_text)
            
            # Try to find morphological info
            morph_info = None
            parent = link.find_parent(['td', 'div', 'li'])
            if parent:
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


async def scrape_pages_batch(session: aiohttp.ClientSession, page_range: range, semaphore: asyncio.Semaphore) -> List[Lemma]:
    """Scrape multiple pages concurrently with rate limiting."""
    async def scrape_with_semaphore(page_num):
        async with semaphore:
            return await scrape_lemma_list_page_async(session, page_num)
    
    tasks = [scrape_with_semaphore(page) for page in page_range]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_lemmas = []
    for result in results:
        if isinstance(result, list):
            all_lemmas.extend(result)
    
    return all_lemmas


async def scrape_inflections_batch(session: aiohttp.ClientSession, lemmas: List[Lemma], semaphore: asyncio.Semaphore) -> List[InflectedForm]:
    """Scrape inflections for multiple lemmas concurrently with rate limiting."""
    async def scrape_with_semaphore(lemma):
        async with semaphore:
            return await scrape_lemma_inflections_async(session, lemma)
    
    tasks = [scrape_with_semaphore(lemma) for lemma in lemmas]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_inflections = []
    for result in results:
        if isinstance(result, list):
            all_inflections.extend(result)
    
    return all_inflections


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


def save_checkpoint(lemmas: List[Lemma], inflections: List[InflectedForm], checkpoint_num: int):
    """Save checkpoint files for resuming."""
    checkpoint_dir = 'database/checkpoints'
    import os
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    with open(f'{checkpoint_dir}/lemmas_checkpoint_{checkpoint_num}.json', 'w', encoding='utf-8') as f:
        json.dump([asdict(l) for l in lemmas], f, ensure_ascii=False, indent=2)
    
    with open(f'{checkpoint_dir}/inflections_checkpoint_{checkpoint_num}.json', 'w', encoding='utf-8') as f:
        json.dump([asdict(i) for i in inflections], f, ensure_ascii=False, indent=2)
    
    print(f'  ✓ Checkpoint {checkpoint_num} saved ({len(lemmas)} lemmas, {len(inflections)} inflections)')


async def main_async():
    """Run the async scraper."""
    print("="*70)
    print("PERSEUS ATLAS LEMMAS AND CONJUGATIONS SCRAPER - ASYNC BATCH")
    print("="*70)
    
    # Configuration
    START_PAGE = 1
    END_PAGE = None  # Set to None to scrape all pages, or a number to limit
    MAX_PAGES = 10000  # Safety limit
    
    CONCURRENT_PAGES = 10  # Number of pages to fetch concurrently
    CONCURRENT_LEMMAS = 15  # Number of lemmas to scrape concurrently
    
    CHECKPOINT_INTERVAL = 1000  # Save checkpoint every N lemmas
    
    start_time = time.time()
    
    # Create aiohttp session with connection pooling
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=20)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Step 1: Scrape lemma lists
        print(f"\nStep 1: Scraping lemma lists with {CONCURRENT_PAGES} concurrent requests")
        print("-"*70)
        
        all_lemmas = []
        page = START_PAGE
        semaphore_pages = asyncio.Semaphore(CONCURRENT_PAGES)
        
        while True:
            if END_PAGE and page > END_PAGE:
                break
            if page - START_PAGE >= MAX_PAGES:
                print(f'Reached safety limit of {MAX_PAGES} pages')
                break
            
            # Scrape batch of pages
            batch_end = min(page + 100, (END_PAGE or page + 100))
            print(f'Fetching pages {page}-{batch_end-1}...')
            
            batch_lemmas = await scrape_pages_batch(session, range(page, batch_end), semaphore_pages)
            
            if not batch_lemmas:
                print(f'No more lemmas found. Stopping at page {page}.')
                break
            
            all_lemmas.extend(batch_lemmas)
            print(f'  -> Collected {len(batch_lemmas)} lemmas (total: {len(all_lemmas)})')
            
            page = batch_end
            
            # Brief pause between batches
            await asyncio.sleep(0.5)
        
        print(f'\n✓ Total lemmas collected: {len(all_lemmas)}')
        
        if not all_lemmas:
            print("No lemmas collected. Exiting.")
            return 1
        
        # Preview
        print(f'\nFirst 10 lemmas:')
        for lemma in all_lemmas[:10]:
            print(f'  {lemma.lemma} (ID: {lemma.atlas_id})')
        
        # Step 2: Scrape inflections in batches
        print(f"\nStep 2: Scraping inflections for ALL {len(all_lemmas)} lemmas")
        print(f"Using {CONCURRENT_LEMMAS} concurrent requests per batch")
        print("-"*70)
        
        all_inflections = []
        semaphore_lemmas = asyncio.Semaphore(CONCURRENT_LEMMAS)
        
        # Process in batches with checkpoints
        batch_size = 500
        checkpoint_counter = 0
        
        for i in range(0, len(all_lemmas), batch_size):
            batch = all_lemmas[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(all_lemmas) + batch_size - 1) // batch_size
            
            print(f'\nBatch {batch_num}/{total_batches}: Processing lemmas {i+1}-{min(i+batch_size, len(all_lemmas))}...')
            
            batch_inflections = await scrape_inflections_batch(session, batch, semaphore_lemmas)
            all_inflections.extend(batch_inflections)
            
            print(f'  -> Collected {len(batch_inflections)} inflections (total: {len(all_inflections)})')
            
            # Save checkpoint periodically
            if (i + batch_size) % CHECKPOINT_INTERVAL < batch_size:
                checkpoint_counter += 1
                save_checkpoint(all_lemmas[:i+batch_size], all_inflections, checkpoint_counter)
            
            # Brief pause between batches
            await asyncio.sleep(0.5)
        
        print(f'\n✓ Total inflected forms collected: {len(all_inflections)}')
    
    # Step 3: Save final results
    print(f"\nStep 3: Saving final results")
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
    elapsed = time.time() - start_time
    print("\n" + "="*70)
    print("SCRAPING SUMMARY - COMPLETE")
    print("="*70)
    print(f'Total runtime: {elapsed/60:.1f} minutes ({elapsed:.0f} seconds)')
    print(f'Total lemmas collected: {len(all_lemmas)}')
    print(f'Total inflected forms found: {len(all_inflections)}')
    if all_inflections and all_lemmas:
        print(f'Average forms per lemma: {len(all_inflections) / len(all_lemmas):.1f}')
    print(f'Speed: {len(all_lemmas) / (elapsed/60):.1f} lemmas/minute')
    print('='*70)
    
    return 0


def main():
    """Entry point that runs the async main."""
    return asyncio.run(main_async())


if __name__ == '__main__':
    sys.exit(main())
