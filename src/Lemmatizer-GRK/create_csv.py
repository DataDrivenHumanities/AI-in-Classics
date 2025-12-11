import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata
import re
import sys
import os
import csv
import time


# CONFIGURATION
INPUT_FILE = 'database/atlas_lemmas.csv'
OUTPUT_FILE = 'database/GREEK_FULL_DATASET.csv'
CONCURRENT_REQUESTS = 30 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Grammar Mapping
GRAMMAR_MAP = {
    'tense': {'pres': 'present', 'fut': 'future', 'aor': 'aorist', 'perf': 'perfect', 'plup': 'pluperfect', 'imperf': 'imperfect', 'futperf': 'future perfect'},
    'voice': {'act': 'active', 'mid': 'middle', 'pass': 'passive', 'mp': 'middle-passive'},
    'mood': {'ind': 'indicative', 'subj': 'subjunctive', 'opt': 'optative', 'imp': 'imperative'},
    'verb_form': {'inf': 'infinitive', 'part': 'participle'},
    'person': {'1st': '1', '2nd': '2', '3rd': '3'},
    'number': {'sg': 'singular', 'pl': 'plural', 'dual': 'dual'},
    'gender': {'masc': 'masculine', 'fem': 'feminine', 'neut': 'neuter'},
    'case': {'nom': 'nominative', 'gen': 'genitive', 'dat': 'dative', 'acc': 'accusative', 'voc': 'vocative'},
    'degree': {'pos': 'positive', 'comp': 'comparative', 'sup': 'superlative'}
}

# HELPER FUNCTIONS

def strip_accents(text):
    """Creates the 'nod' (no diacritics) version."""
    if not isinstance(text, str): return ""
    normalized = unicodedata.normalize('NFD', text)
    return "".join(c for c in normalized if unicodedata.category(c) != 'Mn')

def normalize_greek(text):
    """Standardizes Greek text (NFC) and removes numbers."""
    if not isinstance(text, str): return ""
    text = re.sub(r'\d+', '', text).strip() 
    return unicodedata.normalize('NFC', text)

def expand_pos(pos_abbr):
    """Standardizes POS abbreviations."""
    if not pos_abbr: return ""
    mapping = {
        'art': 'article', 'adj': 'adjective', 'adv': 'adverb',
        'noun': 'noun', 'verb': 'verb', 'part': 'participle',
        'prep': 'preposition', 'conj': 'conjunction', 'pron': 'pronoun',
        'num': 'numeral', 'exclam': 'exclamation', 'punc': 'punctuation'
    }
    return mapping.get(pos_abbr.lower(), pos_abbr.lower())

def parse_morphology(morph_str, raw_pos, page_context_gender=''):
    """Parses grammar string into columns."""
    result = {k: '' for k in GRAMMAR_MAP.keys()}
    result['label'] = expand_pos(raw_pos)
    
    if not morph_str: 
        if page_context_gender: result['gender'] = page_context_gender
        return result

    clean_str = morph_str.replace("(", "").replace(")", "").replace(",", " ").lower()
    tokens = clean_str.split()

    for token in tokens:
        for category, mapping in GRAMMAR_MAP.items():
            if token in mapping:
                result[category] = mapping[token]
                break
    
    # Use context gender if tooltip missed it
    if not result['gender'] and page_context_gender:
        result['gender'] = page_context_gender

    # Infer Label
    if result['tense'] or result['voice'] or result['mood']:
        result['label'] = 'verb'
        if result['verb_form'] == 'participle': result['label'] = 'participle'
    elif result['case']:
        if 'art' in clean_str: result['label'] = 'article'
        elif 'adj' in clean_str: result['label'] = 'adjective'
        elif not result['label']: result['label'] = 'noun'
        
    return result

def is_garbage(lemma):
    """Filters out punctuation and bad entries."""
    if not lemma: return True
    lemma = str(lemma).strip()
    if re.search(r'[\[\]\d]', lemma): return True
    if len(lemma) == 1 and not lemma.isalpha(): return True
    if lemma in [",", ".", "·", ";"]: return True
    return False


# CORE SCRAPING LOGIC

async def process_lemma_page(session, row, semaphore):
    url = row['url']
    lemma_diac = row['lemma']
    atlas_id = row['atlas_id']
    lemma_nod = strip_accents(lemma_diac)
    
    rows_to_write = []

    async with semaphore:
        try:
            async with session.get(url, headers=HEADERS, timeout=30) as response:
                if response.status == 429:
                    print(f"⚠️ 429 Blocked on {lemma_diac}. Retrying in 5s...")
                    await asyncio.sleep(5)
                    return await process_lemma_page(session, row, semaphore)
                
                if response.status != 200: return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # --- 1. METADATA (POS & Definition) ---
                raw_pos = ""
                definition = ""
                
                h1 = soup.find('h1')
                if h1:
                    pos_tag = h1.find('small') or h1.find('span')
                    if pos_tag: 
                        raw_pos = pos_tag.get_text(strip=True).lower()
                    else:
                        text = h1.get_text(" ", strip=True)
                        parts = text.split()
                        if len(parts) > 1 and parts[-1].isupper() and len(parts[-1]) > 1:
                            raw_pos = parts[-1].lower()

                # Definition Extraction
                short_def = soup.find(lambda tag: tag.name in ['h2','h3','h4','strong'] and "ShortDef" in tag.get_text())
                if short_def:
                    sib = short_def.find_next_sibling()
                    if sib: 
                        definition = sib.get_text(strip=True)
                        # CLEANUP: Remove Dictionary Suffixes
                        bad_suffixes = ["LSJ", "Middle Liddell", "Slater", "Autenrieth"]
                        for suffix in bad_suffixes:
                            if definition.endswith(suffix):
                                definition = definition[:-len(suffix)].strip()
                
                # Fallback Definition
                if not definition:
                    title = soup.title.string if soup.title else ""
                    if "-" in title:
                        parts = title.split("-", 1)
                        if len(parts) > 1:
                            clean_part = parts[1].strip()
                            clean_part = clean_part.replace("Perseus", "").replace("Scaife ATLAS", "").strip()
                            definition = clean_part

                # Infer Gender from Definition text
                gender_str = ""
                def_lower = definition.lower()
                if "masc" in def_lower: gender_str = "masculine"
                elif "fem" in def_lower: gender_str = "feminine"
                elif "neut" in def_lower: gender_str = "neuter"

                # --- 2. EXTRACT FORMS with CONTEXT ---
                tables = soup.find_all('table')
                seen_forms = set()

                for table in tables:
                    # Context Gender (Header above table)
                    page_context_gender = ""
                    prev_header = table.find_previous(['h2', 'h3', 'h4'])
                    if prev_header:
                        header_text = prev_header.get_text(strip=True).upper()
                        if "MASCULINE" in header_text: page_context_gender = "masculine"
                        elif "FEMININE" in header_text: page_context_gender = "feminine"
                        elif "NEUTER" in header_text: page_context_gender = "neuter"

                    links = table.find_all('a', href=re.compile(r'/form/\d+/'))
                    
                    for link in links:
                        raw_text = link.get_text(strip=True)
                        form_diac = normalize_greek(raw_text)
                        
                        if not form_diac or form_diac in [",", "."] or "TOTAL" in raw_text: 
                            continue

                        # Tooltip Strategy
                        morph_str = link.get('title', '')
                        if '(' in morph_str:
                            morph_str = morph_str.split('(')[-1].replace(')', '').strip()

                        # Fallback Strategy
                        if not morph_str or "lemma" in morph_str:
                            parent_td = link.find_parent('td')
                            if parent_td:
                                next_td = parent_td.find_next_sibling('td')
                                if next_td:
                                    candidate = next_td.get_text(strip=True)
                                    if not candidate.isdigit():
                                        morph_str = candidate

                        unique_key = (form_diac, morph_str, page_context_gender)
                        if unique_key in seen_forms: continue
                        seen_forms.add(unique_key)

                        # --- 3. PARSE ---
                        grammar = parse_morphology(morph_str, raw_pos, page_context_gender)
                        
                        # Refine POS Label
                        final_label = grammar['label']
                        final_gender = grammar['gender'] if grammar['gender'] else gender_str
                        
                        if final_label == 'noun' and final_gender:
                            final_label = f"{final_gender} noun"

                        entry = {
                            'lemma_nod': lemma_nod,
                            'form_nod': strip_accents(form_diac),
                            'form_diac': form_diac,
                            'label': final_label,
                            'mood': grammar['mood'],
                            'tense': grammar['tense'],
                            'voice': grammar['voice'],
                            'person': grammar['person'],
                            'number': grammar['number'],
                            'gender': final_gender,
                            'case': grammar['case'],
                            'degree': grammar['degree'],
                            'verb_form': grammar['verb_form'],
                            'page_url': url,
                            'english_definition': definition,
                            'morphology': morph_str,
                            'atlas_id': atlas_id
                        }
                        rows_to_write.append(entry)

        except Exception:
            pass
            
    return rows_to_write

# MAIN EXECUTION

async def main():
    print("="*60)
    print("STARTING GREEK SCRAPING")
    print("="*60)
    
    if not os.path.exists(INPUT_FILE):
        print(f"Critical Error: Input file '{INPUT_FILE}' not found.")
        return

    # 1. Load Data
    print("Loading Lemma List...")
    df = pd.read_csv(INPUT_FILE)
    df = df[~df['lemma'].apply(is_garbage)]
    
    # 2. Optimize
    unique_rows = df.drop_duplicates(subset=['url'])
    print(f"⚡ Optimized: {len(unique_rows)} unique pages to visit.")

    # 3. Setup Output
    fieldnames = [
        'lemma_nod', 'form_nod', 'form_diac', 'label', 
        'mood', 'tense', 'voice', 'person', 'number', 
        'gender', 'case', 'degree', 'verb_form', 
        'page_url', 'english_definition', 'morphology', 'atlas_id'
    ]
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    # 4. Run Pipeline
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    connector = aiohttp.TCPConnector(limit=CONCURRENT_REQUESTS + 10)
    
    total_saved = 0
    start_time = time.time()

    async with aiohttp.ClientSession(connector=connector) as session:
        CHUNK_SIZE = 500
        lemmas_list = [row for _, row in unique_rows.iterrows()]
        
        for i in range(0, len(lemmas_list), CHUNK_SIZE):
            batch = lemmas_list[i : i+CHUNK_SIZE]
            tasks = [process_lemma_page(session, row, semaphore) for row in batch]
            results = await asyncio.gather(*tasks)
            
            flat_results = [item for sublist in results for item in sublist]
            
            if flat_results:
                with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writerows(flat_results)
                total_saved += len(flat_results)
            
            elapsed = time.time() - start_time
            print(f"   💾 Batch {i}-{i+len(batch)} complete. Total Rows: {total_saved} ({elapsed/60:.1f}m)")

    # 5. SORTING STEP (Runs at the very end)
    print("Sorting Final Dataset by Lemma ID...")
    try:
        final_df = pd.read_csv(OUTPUT_FILE)
        # Ensure numeric sorting
        final_df['sort_key'] = pd.to_numeric(final_df['atlas_id'], errors='coerce')
        final_df = final_df.sort_values('sort_key').drop(columns=['sort_key'])
        final_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        print("Sorting Complete.")
    except Exception as e:
        print(f"⚠️ Sorting skipped (Error: {e}) - File is still valid.")

    print("\n" + "="*60)
    print(f"PIPELINE COMPLETE")
    print(f"   Output File: {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())