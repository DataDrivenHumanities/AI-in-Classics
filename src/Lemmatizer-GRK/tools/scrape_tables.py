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
    Finds any link pointing to a lemma detail page.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    urls = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if "/lemma/" in href and "?lang=" not in href:
            full_url = urljoin(BASE_URL, href)
            urls.append(full_url)
    # Remove duplicates just in case
    return list(set(urls))

def parse_flexion_tables(html_text, page_url):
    """
    Scrapes the details page for paradigm forms using the Forms List.
    Returns (lemma_text, list_of_rows)
    """
    soup = BeautifulSoup(html_text, "html.parser")
    rows = []
    # extract lemma header
    header = soup.find('h1') or soup.find('h2')
    raw_lemma_text = header.get_text(" ", strip=True) if header else "unknown_lemma"
    cleaned_string = raw_lemma_text.replace("Lemma:", "").split("(")[0].strip()
    if not cleaned_string:
        lemma_id = page_url.strip("/").split("/")[-1]
        lemma_text = f"unknown_{lemma_id}"
        print(f"Warning: No lemma text found for {page_url}. Saved as {lemma_text}")
    else:
        lemma_text = cleaned_string.split()[0]
    # find Forms List table
    target_table = None
    for table in soup.find_all('table'):
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        if "form" in headers and "parse" in headers:
            target_table = table
            break
    # if Forms List table doesn't exist for some reason? may need to add error message too.
    if not target_table:
        return lemma_text, []
    tbody = target_table.find('tbody') or target_table
    # loops through all table rows
    for tr in tbody.find_all('tr'):
        tds = tr.find_all(['td', 'th'])
        if len(tds) < 2:
            continue
        # grabs Greek word and code
        raw_form = tds[0].get_text(" ", strip=True)
        if raw_form.lower() == "form": continue
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

# async network logic
async def fetch_text(session, url, timeout=20, retries=4, delay=0.2):
    """
    Downloads a webpage, using Exponential Backoff to keep trying regardless if server is busy or internet is down.
    """
    for attempt in range(retries + 1):
        try:
            # try to download the page, check for errors 
            async with session.get(url, timeout=timeout) as resp:
                resp.raise_for_status()
                return await resp.text()
        except (ClientResponseError, ClientConnectorError, asyncio.TimeoutError):
            if attempt >= retries: raise
            backoff = delay * (2 ** attempt) + random.uniform(0, delay)
            await asyncio.sleep(backoff)
    
async def fetch_and_write_lemma(session, url, outdir, sem, delay):
    """
    Worker function: Fetches detail page, parses, saves it to CSV.
    """
    # Wait for free worker slot
    async with sem:
        try:
            html = await fetch_text(session, url)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return 0
        # Run parser
        lemma_text, rows = parse_flexion_tables(html, url)
        if re.match(r'^[^\w]+$', lemma_text) or lemma_text in [",", ".", ";", "·", ":"]:
            print(f"    [Skipping] Punctuation lemma: {lemma_text}")
            return 0
        if not rows:
            return 0
        # ensure filenames are okay
        safe_name = slugify_lemma(lemma_text)
        if not safe_name: safe_name = "unknown_lemma"
        # save to csv
        path = outdir / f"{safe_name}.csv"
        headers = [
            "lemma_text", "form", "pos", "case", "number", "gender",
            "person", "tense", "mood", "voice", "page_url", "raw_parse"
        ]
        # define headers based off keys in parser dictionary
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        if delay > 0: await asyncio.sleep(delay)
        return len(rows)

async def main():
    # creates parser
    parser = argparse.ArgumentParser()
    # Defines arguments
    parser.add_argument("--outdir", default="src/Lemmatizer-GRK/out", help="Dictionary to save CSVs")
    parser.add_argument("--start", type=int, default=1, help="Start page of index")
    parser.add_argument("--end", type=int, default=1, help="End page of index")
    parser.add_argument("--index-concurrency", type=int, default=4, help="Simultaneous index pages")
    parser.add_argument("--lemma-concurrency", type=int, default=10, help="Simultaneous detail pages")
    parser.add_argument("--delay", type=float, default=0.1, help="Wait time between requests")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    # Sets up TCP connections, limits to 50 open connections
    connector = aiohttp.TCPConnector(limit=50, ssl=False)
    # Establishes 20 second timeout limit
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=20, sock_read=20)
    # Opens client session
    async with aiohttp.ClientSession(headers=HEADERS, connector=connector, timeout=timeout) as session:
        print(f"Scanning Index Pages {args.start} to {args.end}")
        all_lemmas_urls=set()
        # Uses semaphore to ensure only index_concurrency pages are being downloaded at once
        index_sem = asyncio.Semaphore(args.index_concurrency)
        # Mini worker - runs parse_index_for_urls, returns list of URLs found on page
        async def process_index_page(pg):
            async with index_sem:
                url = INDEX_URL.format(pg=pg)
                try:
                    txt = await fetch_text(session, url)
                    urls = parse_index_for_urls(txt)
                    print(f"[{pg}]: Found {len(urls)} lemmas")
                    return urls
                except Exception as e:
                    print(f"[{pg}] Failed: {e}")
                    return []
            # list of pending pages
        tasks = [process_index_page(pg) for pg in range(args.start, args.end + 1)]
        results = await asyncio.gather(*tasks)
        for res in results:
            all_lemmas_urls.update(res)
        print(f"Found {len(all_lemmas_urls)} unique lemmas.")
        print("Scraping Details...")
        # New semaphore for grabbing lemma
        lemma_sem = asyncio.Semaphore(args.lemma_concurrency)
        # list of all jobs 
        tasks = [
            fetch_and_write_lemma(session, url, outdir, lemma_sem, args.delay)
            for url in all_lemmas_urls
        ]
        done_count = 0
        total_rows = 0
        total_tasks = len(tasks)
        for coro in asyncio.as_completed(tasks):
            # number of rows saved for particular word
            res = await coro
            # files completed
            done_count += 1
            # total num db rows
            total_rows += res
            if done_count % 10 == 0 or done_count == total_tasks:
                print(f"{done_count} / {total_tasks} lemmas processed.")
        print(f"Saved {total_rows} rows to {outdir}")

if __name__ == "__main__":
    asyncio.run(main())