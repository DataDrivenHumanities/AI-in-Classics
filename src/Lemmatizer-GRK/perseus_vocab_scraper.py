#!/usr/bin/env python3
"""
Perseus Vocabulary Scraper

Scrapes Greek lemmas from:
1. https://vocab.perseus.org/lemma/ - Lemmas with corpus frequency and meanings
2. https://atlas.perseus.tufts.edu/lemmas/?lang=grc - Paginated lemma list

This scraper extracts:
- Greek lemmas
- Definitions/glosses
- Frequency data
- Links to detailed entries
"""

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Base URLs
VOCAB_BASE = "https://vocab.perseus.org"
ATLAS_BASE = "https://atlas.perseus.tufts.edu"

HEADERS = {
    'User-Agent': 'AI-in-Classics Perseus Scraper (+https://github.com/DataDrivenHumanities/AI-in-Classics)'
}


@dataclass
class PerseusLemma:
    """Represents a Greek lemma from Perseus."""
    lemma: str
    lemma_id: Optional[str] = None
    url: str = ""
    source: str = "perseus"
    language: str = "grc"
    
    # From vocab.perseus.org
    corpus_count: Optional[int] = None
    corpus_freq: Optional[float] = None
    core_count: Optional[int] = None
    core_freq: Optional[float] = None
    definition: Optional[str] = None
    gloss: Optional[str] = None
    
    # From atlas
    atlas_id: Optional[str] = None


class PerseusVocabScraper:
    """
    Scraper for Perseus vocabulary tools.
    
    Example:
        >>> scraper = PerseusVocabScraper()
        >>> lemmas = scraper.scrape_vocab_page(limit=100)
        >>> scraper.save_to_csv(lemmas, "perseus_lemmas.csv")
    """
    
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
    
    def fetch(self, url: str, timeout: int = 30) -> str:
        """Fetch URL content."""
        resp = self.session.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    
    def scrape_vocab_page(self, page: int = 1, limit: Optional[int] = None) -> List[PerseusLemma]:
        """
        Scrape lemmas from vocab.perseus.org.
        
        Args:
            page: Page number to scrape
            limit: Maximum number of lemmas to return
            
        Returns:
            List of PerseusLemma objects
        """
        url = f"{VOCAB_BASE}/lemma/?page={page}"
        print(f"Fetching: {url}")
        
        html = self.fetch(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        lemmas = []
        
        # Find lemma table or list
        # The page shows lemmas as links with frequency data
        lemma_links = soup.find_all('a', href=re.compile(r'/lemma/\d+/'))
        
        for link in lemma_links:
            if limit and len(lemmas) >= limit:
                break
            
            lemma_text = link.get_text(strip=True)
            lemma_url = urljoin(VOCAB_BASE, link['href'])
            
            # Extract lemma ID from URL
            lemma_id_match = re.search(r'/lemma/(\d+)/', lemma_url)
            lemma_id = lemma_id_match.group(1) if lemma_id_match else None
            
            lemma = PerseusLemma(
                lemma=lemma_text,
                lemma_id=lemma_id,
                url=lemma_url,
                source="vocab.perseus.org"
            )
            
            # Try to extract frequency data from surrounding elements
            parent = link.parent
            if parent:
                # Look for frequency counts in the same row
                text = parent.get_text()
                # Parse counts if present (format varies)
                counts = re.findall(r'(\d+)', text)
                if len(counts) >= 2:
                    try:
                        lemma.corpus_count = int(counts[0])
                        lemma.core_count = int(counts[1]) if len(counts) > 1 else None
                    except ValueError:
                        pass
            
            lemmas.append(lemma)
        
        return lemmas
    
    def scrape_lemma_detail(self, lemma_id: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed information for a specific lemma.
        
        Args:
            lemma_id: Perseus lemma ID
            
        Returns:
            Dictionary with lemma details including definition
        """
        url = f"{VOCAB_BASE}/lemma/{lemma_id}/"
        print(f"Fetching detail: {url}")
        
        try:
            html = self.fetch(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            details = {
                'lemma_id': lemma_id,
                'url': url
            }
            
            # Extract lemma headword
            heading = soup.find('h1') or soup.find('h2')
            if heading:
                details['lemma'] = heading.get_text(strip=True)
            
            # Extract definition/gloss
            # Look for definition in various possible locations
            definition_elem = soup.find('div', class_='definition') or \
                            soup.find('p', class_='gloss') or \
                            soup.find('div', class_='meaning')
            
            if definition_elem:
                details['definition'] = definition_elem.get_text(strip=True)
            
            # Extract frequency/count data
            stats = soup.find('div', class_='statistics') or soup.find('table')
            if stats:
                text = stats.get_text()
                # Parse statistics
                corpus_match = re.search(r'corpus.*?(\d+)', text, re.IGNORECASE)
                if corpus_match:
                    details['corpus_count'] = int(corpus_match.group(1))
                
                core_match = re.search(r'core.*?(\d+)', text, re.IGNORECASE)
                if core_match:
                    details['core_count'] = int(core_match.group(1))
            
            return details
            
        except Exception as e:
            print(f"Error fetching lemma {lemma_id}: {e}", file=sys.stderr)
            return None
    
    def scrape_atlas_page(self, page: int = 1, limit: Optional[int] = None) -> List[PerseusLemma]:
        """
        Scrape lemmas from atlas.perseus.tufts.edu.
        
        Args:
            page: Page number to scrape
            limit: Maximum number of lemmas to return
            
        Returns:
            List of PerseusLemma objects
        """
        url = f"{ATLAS_BASE}/lemmas/?lang=grc&page={page}"
        print(f"Fetching: {url}")
        
        html = self.fetch(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        lemmas = []
        
        # Find all lemma links
        lemma_links = soup.find_all('a', href=re.compile(r'/lemma/\d+/'))
        
        for link in lemma_links:
            if limit and len(lemmas) >= limit:
                break
            
            lemma_text = link.get_text(strip=True)
            
            # Skip navigation and non-Greek text
            if not lemma_text or lemma_text in ['start', 'prev', 'next', 'end']:
                continue
            
            lemma_url = urljoin(ATLAS_BASE, link['href'])
            
            # Extract atlas ID from URL
            atlas_id_match = re.search(r'/lemma/(\d+)/', lemma_url)
            atlas_id = atlas_id_match.group(1) if atlas_id_match else None
            
            lemma = PerseusLemma(
                lemma=lemma_text,
                atlas_id=atlas_id,
                url=lemma_url,
                source="atlas.perseus.tufts.edu"
            )
            
            lemmas.append(lemma)
        
        return lemmas
    
    def scrape_multiple_pages(
        self,
        source: str = "vocab",
        start_page: int = 1,
        num_pages: int = 10,
        delay: float = 1.0
    ) -> List[PerseusLemma]:
        """
        Scrape multiple pages from Perseus.
        
        Args:
            source: Either "vocab" or "atlas"
            start_page: Starting page number
            num_pages: Number of pages to scrape
            delay: Delay between requests in seconds
            
        Returns:
            List of all scraped lemmas
        """
        all_lemmas = []
        
        for page in range(start_page, start_page + num_pages):
            try:
                if source == "vocab":
                    lemmas = self.scrape_vocab_page(page=page)
                elif source == "atlas":
                    lemmas = self.scrape_atlas_page(page=page)
                else:
                    raise ValueError(f"Unknown source: {source}")
                
                all_lemmas.extend(lemmas)
                print(f"Page {page}: collected {len(lemmas)} lemmas (total: {len(all_lemmas)})")
                
                time.sleep(delay)
                
            except Exception as e:
                print(f"Error scraping page {page}: {e}", file=sys.stderr)
                continue
        
        return all_lemmas
    
    def enrich_with_details(
        self,
        lemmas: List[PerseusLemma],
        delay: float = 1.0,
        limit: Optional[int] = None
    ) -> List[PerseusLemma]:
        """
        Enrich lemmas with detailed information from individual pages.
        
        Args:
            lemmas: List of basic lemma objects
            delay: Delay between requests
            limit: Maximum number to enrich
            
        Returns:
            List of enriched lemmas
        """
        enriched = []
        
        for i, lemma in enumerate(lemmas):
            if limit and i >= limit:
                break
            
            if lemma.lemma_id:
                details = self.scrape_lemma_detail(lemma.lemma_id)
                
                if details:
                    # Update lemma with details
                    if 'definition' in details:
                        lemma.definition = details['definition']
                    if 'corpus_count' in details:
                        lemma.corpus_count = details['corpus_count']
                    if 'core_count' in details:
                        lemma.core_count = details['core_count']
                
                time.sleep(delay)
            
            enriched.append(lemma)
            
            if (i + 1) % 10 == 0:
                print(f"Enriched {i + 1}/{len(lemmas)} lemmas...")
        
        return enriched
    
    def save_to_csv(self, lemmas: List[PerseusLemma], output_file: str):
        """Save lemmas to CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'lemma', 'lemma_id', 'atlas_id', 'url', 'source', 'language',
                'corpus_count', 'corpus_freq', 'core_count', 'core_freq',
                'definition', 'gloss'
            ])
            writer.writeheader()
            
            for lemma in lemmas:
                writer.writerow(asdict(lemma))
        
        print(f"✓ Saved {len(lemmas)} lemmas to {output_file}")
    
    def save_to_json(self, lemmas: List[PerseusLemma], output_file: str):
        """Save lemmas to JSON."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(lemma) for lemma in lemmas], f, ensure_ascii=False, indent=2)
        
        print(f"✓ Saved {len(lemmas)} lemmas to {output_file}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Scrape Greek lemmas from Perseus vocabulary tools'
    )
    parser.add_argument('--source', choices=['vocab', 'atlas', 'both'], default='vocab',
                       help='Source to scrape from')
    parser.add_argument('--output', required=True, help='Output CSV file')
    parser.add_argument('--format', choices=['csv', 'json'], default='csv',
                       help='Output format')
    parser.add_argument('--pages', type=int, default=10,
                       help='Number of pages to scrape')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Starting page number')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between requests (seconds)')
    parser.add_argument('--enrich', action='store_true',
                       help='Fetch detailed info for each lemma (slower)')
    parser.add_argument('--enrich-limit', type=int,
                       help='Limit number of lemmas to enrich')
    
    args = parser.parse_args()
    
    try:
        scraper = PerseusVocabScraper()
        
        all_lemmas = []
        
        if args.source in ['vocab', 'both']:
            print(f"\nScraping vocab.perseus.org...")
            vocab_lemmas = scraper.scrape_multiple_pages(
                source='vocab',
                start_page=args.start_page,
                num_pages=args.pages,
                delay=args.delay
            )
            all_lemmas.extend(vocab_lemmas)
        
        if args.source in ['atlas', 'both']:
            print(f"\nScraping atlas.perseus.tufts.edu...")
            atlas_lemmas = scraper.scrape_multiple_pages(
                source='atlas',
                start_page=args.start_page,
                num_pages=args.pages,
                delay=args.delay
            )
            all_lemmas.extend(atlas_lemmas)
        
        # Enrich with details if requested
        if args.enrich:
            print(f"\nEnriching lemmas with detailed information...")
            all_lemmas = scraper.enrich_with_details(
                all_lemmas,
                delay=args.delay,
                limit=args.enrich_limit
            )
        
        # Deduplicate by lemma text
        seen = set()
        unique_lemmas = []
        for lemma in all_lemmas:
            if lemma.lemma not in seen:
                seen.add(lemma.lemma)
                unique_lemmas.append(lemma)
        
        print(f"\nTotal lemmas: {len(all_lemmas)}")
        print(f"Unique lemmas: {len(unique_lemmas)}")
        
        # Save output
        if args.format == 'csv':
            scraper.save_to_csv(unique_lemmas, args.output)
        else:
            scraper.save_to_json(unique_lemmas, args.output)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
