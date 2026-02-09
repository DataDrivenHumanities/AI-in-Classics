# Greek Lemmatizer Technical Guide

This document provides detailed technical guidance for implementing the Greek lemmatizer workflow as outlined in the workflow diagram.

## 1. HTML Scraping from Wiktionary

The workflow begins by collecting Greek lexical data from Wiktionary or other Greek dictionary sources.

### Technical Implementation

```python
def scrape_wiktionary_greek_entry(word):
    """
    Scrape a Greek word entry from Wiktionary
    
    Args:
        word: Greek word to look up
        
    Returns:
        HTML content of the Greek section
    """
    url = f"https://en.wiktionary.org/wiki/{word}"
    headers = {
        'User-Agent': 'GreekLemmatizerBot/1.0 (research@classics.edu)'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the Greek language section
        greek_section = None
        for h2 in soup.find_all('h2'):
            span = h2.find('span', {'id': 'Greek', 'class': 'mw-headline'})
            if span:
                greek_section = h2
                break
                
        if greek_section:
            # Extract content until next h2
            content = []
            current = greek_section.next_sibling
            while current and current.name != 'h2':
                content.append(str(current))
                current = current.next_sibling
                
            return ''.join(content)
    
    return None
```

**Key Considerations:**
- Respect rate limits to avoid overloading dictionary servers
- Normalize Unicode for Greek characters (NFC normalization recommended)
- Implement error handling for failed requests
- Consider caching responses to minimize redundant requests

## 2. Extracting Tables from HTML

After obtaining the HTML content, the next step is to extract structured information.

### Technical Implementation

```python
def extract_grammatical_tables(html_content):
    """
    Extract grammatical information tables from HTML
    
    Args:
        html_content: HTML content of Greek word entry
        
    Returns:
        Dictionary with grammatical tables
    """
    if not html_content:
        return {}
        
    soup = BeautifulSoup(html_content, 'html.parser')
    result = {
        'definitions': [],
        'declension_tables': [],
        'conjugation_tables': [],
        'etymology': None,
        'part_of_speech': None
    }
    
    # Extract definitions
    ol_lists = soup.find_all('ol')
    for ol in ol_lists:
        if ol.parent and ol.parent.name == 'div':
            definitions = [li.get_text().strip() for li in ol.find_all('li')]
            if definitions:
                result['definitions'] = definitions
                break
    
    # Extract part of speech
    pos_headers = soup.find_all('span', class_='mw-headline')
    for header in pos_headers:
        if header.get_text() in ['Noun', 'Verb', 'Adjective', 'Adverb']:
            result['part_of_speech'] = header.get_text().lower()
            break
            
    # Extract declension/conjugation tables
    tables = soup.find_all('table', class_='inflection-table')
    for table in tables:
        if 'declension' in table.get_text().lower():
            result['declension_tables'].append(_parse_table(table))
        elif 'conjugation' in table.get_text().lower():
            result['conjugation_tables'].append(_parse_table(table))
    
    return result
    
def _parse_table(table):
    """Parse an HTML table into a structured dictionary"""
    result = {'headers': [], 'rows': []}
    
    # Extract headers
    headers = table.find_all('th')
    result['headers'] = [h.get_text().strip() for h in headers]
    
    # Extract rows
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if cells:
            result['rows'].append([c.get_text().strip() for c in cells])
            
    return result
```

**Key Considerations:**
- Handle different table structures that may exist across word types
- Implement robust error handling for malformed HTML
- Extract all relevant grammatical information (declension, conjugation, irregular forms)

## 3. Scraping Tables per Word

With the extraction logic in place, we can process multiple words to build a comprehensive dataset.

### Technical Implementation

```python
def process_greek_word_list(word_list, output_dir):
    """
    Process a list of Greek words to extract grammatical information
    
    Args:
        word_list: List of Greek words to process
        output_dir: Directory to save intermediate results
    
    Returns:
        Dictionary mapping words to their grammatical data
    """
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    
    for i, word in enumerate(word_list):
        print(f"Processing {i+1}/{len(word_list)}: {word}")
        
        # Scrape HTML
        html_content = scrape_wiktionary_greek_entry(word)
        
        # Extract tables
        if html_content:
            word_data = extract_grammatical_tables(html_content)
            results[word] = word_data
            
            # Save intermediate results
            with open(os.path.join(output_dir, f"{word}.json"), 'w', encoding='utf-8') as f:
                json.dump(word_data, f, ensure_ascii=False, indent=2)
        
        # Respect rate limits
        time.sleep(1)
    
    return results
```

**Key Considerations:**
- Save intermediate results to avoid data loss during long-running processes
- Implement progress tracking for visibility during execution
- Consider parallelizing with proper rate limiting to improve throughput

## 4. Creating CSV Files for Persistent Storage

After extracting grammatical data, organize it into structured CSV files by part of speech.

### Technical Implementation

```python
def create_csv_files(word_data, output_dir):
    """
    Create CSV files from processed word data
    
    Args:
        word_data: Dictionary mapping words to grammatical data
        output_dir: Directory to save CSV files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare data structures for different parts of speech
    nouns_data = []
    verbs_data = []
    adjectives_data = []
    adverbs_data = []
    
    for word, data in word_data.items():
        pos = data.get('part_of_speech')
        if not pos:
            continue
            
        base_entry = {
            'FPP': word,
            'English': '; '.join(data.get('definitions', [])) if data.get('definitions') else 'NULL',
            'Sentiment': 'NULL'  # Placeholder for sentiment analysis
        }
        
        if pos == 'noun':
            nouns_data.append(_enhance_noun_entry(base_entry, data))
        elif pos == 'verb':
            verbs_data.append(_enhance_verb_entry(base_entry, data))
        elif pos == 'adjective':
            adjectives_data.append(_enhance_adj_entry(base_entry, data))
        elif pos == 'adverb':
            adverbs_data.append(base_entry)  # Adverbs typically need less enhancement
    
    # Write to CSV files
    _write_to_csv(os.path.join(output_dir, 'nouns.csv'), nouns_data)
    _write_to_csv(os.path.join(output_dir, 'verbs.csv'), verbs_data)
    _write_to_csv(os.path.join(output_dir, 'adjectives.csv'), adjectives_data)
    _write_to_csv(os.path.join(output_dir, 'adverbs.csv'), adverbs_data)
    
def _enhance_noun_entry(base_entry, data):
    """Add noun-specific fields to the entry"""
    # Extract gender, declension type, etc.
    enhanced = base_entry.copy()
    
    # Extract declension information if available
    if data.get('declension_tables'):
        table = data['declension_tables'][0]
        # Logic to extract declension patterns
        # This is simplified - would need customization based on actual table structure
        
    return enhanced

def _enhance_verb_entry(base_entry, data):
    """Add verb-specific fields to the entry"""
    enhanced = base_entry.copy()
    # Similar logic for verb entries
    return enhanced

def _enhance_adj_entry(base_entry, data):
    """Add adjective-specific fields to the entry"""
    enhanced = base_entry.copy()
    # Similar logic for adjective entries
    return enhanced

def _write_to_csv(filepath, entries):
    """Write entries to a CSV file"""
    if not entries:
        return
        
    fieldnames = entries[0].keys()
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entries)
```

**Key Considerations:**
- Ensure consistent structure across all entries
- Implement proper handling of missing data
- Handle Unicode encoding correctly for Greek text

## 5. Importing to Relational Database

After creating CSV files, import the data into a relational database for efficient querying.

### Technical Implementation

```python
def import_to_database(csv_dir, db_config):
    """
    Import CSV data into PostgreSQL database
    
    Args:
        csv_dir: Directory containing CSV files
        db_config: Database configuration parameters
    """
    # Connect to database
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS greek_lemmas (
        id SERIAL PRIMARY KEY,
        lemma TEXT NOT NULL,
        part_of_speech TEXT NOT NULL,
        definition TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS greek_forms (
        id SERIAL PRIMARY KEY,
        form TEXT NOT NULL,
        lemma_id INTEGER REFERENCES greek_lemmas(id),
        form_type TEXT,
        morphology JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    
    # Import noun data
    with open(os.path.join(csv_dir, 'nouns.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Insert lemma
            cursor.execute(
                "INSERT INTO greek_lemmas (lemma, part_of_speech, definition) VALUES (%s, %s, %s) RETURNING id",
                (row['FPP'], 'noun', row['English'])
            )
            lemma_id = cursor.fetchone()[0]
            
            # Insert forms (would need to parse from the row data)
            # This is simplified and would need customization
            
    # Similar logic for other parts of speech
    
    conn.commit()
    conn.close()
```

**Key Considerations:**
- Implement proper transactions for data integrity
- Create appropriate indices for common query patterns
- Consider using COPY command for bulk imports for better performance

## 6. Python Package for Abstract Querying

The final step is to create a Python package that provides a clean interface for querying the lemmatizer.

### Technical Implementation

```python
class GreekLemmatizer:
    """
    Greek lemmatizer class that provides an interface to the database
    """
    
    def __init__(self, db_config):
        """
        Initialize the lemmatizer with database configuration
        
        Args:
            db_config: Database configuration parameters
        """
        self.conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
        )
        
        # Initialize cache
        self.cache = {}
        
    def lemmatize(self, word):
        """
        Convert an inflected Greek word to its lemma
        
        Args:
            word: Greek word to lemmatize
            
        Returns:
            List of possible lemmas with part of speech
        """
        # Check cache first
        if word in self.cache:
            return self.cache[word]
            
        cursor = self.conn.cursor()
        
        # First try exact match
        cursor.execute("""
        SELECT l.id, l.lemma, l.part_of_speech, l.definition
        FROM greek_forms f
        JOIN greek_lemmas l ON f.lemma_id = l.id
        WHERE f.form = %s
        """, (word,))
        
        results = cursor.fetchall()
        
        # If no exact match, try with normalization
        if not results:
            normalized_word = self._normalize_greek(word)
            cursor.execute("""
            SELECT l.id, l.lemma, l.part_of_speech, l.definition
            FROM greek_forms f
            JOIN greek_lemmas l ON f.lemma_id = l.id
            WHERE f.form = %s
            """, (normalized_word,))
            results = cursor.fetchall()
        
        # If still no match, try with stemming
        if not results:
            stems = self._generate_possible_stems(word)
            for stem in stems:
                cursor.execute("""
                SELECT l.id, l.lemma, l.part_of_speech, l.definition
                FROM greek_forms f
                JOIN greek_lemmas l ON f.lemma_id = l.id
                WHERE f.form LIKE %s
                LIMIT 5
                """, (stem + '%',))
                stem_results = cursor.fetchall()
                if stem_results:
                    results = stem_results
                    break
                    
        # Format results
        formatted_results = [
            {
                'lemma': row[1],
                'pos': row[2],
                'definition': row[3]
            }
            for row in results
        ]
        
        # Cache results
        self.cache[word] = formatted_results
        
        return formatted_results
        
    def _normalize_greek(self, word):
        """
        Normalize Greek Unicode characters
        """
        import unicodedata
        return unicodedata.normalize('NFC', word)
        
    def _generate_possible_stems(self, word):
        """
        Generate possible stems for a Greek word based on common endings
        """
        # This would contain Greek morphology rules
        # Simplified example:
        stems = []
        
        # Remove common endings
        if len(word) > 2:
            stems.append(word[:-1])  # Remove last character
        if len(word) > 3:
            stems.append(word[:-2])  # Remove last two characters
            
        return stems
        
    def get_definition(self, word):
        """
        Get the English definition for a Greek word
        
        Args:
            word: Greek word to define
            
        Returns:
            List of definitions
        """
        lemmas = self.lemmatize(word)
        return [l['definition'] for l in lemmas if l['definition']]
        
    def get_all_forms(self, lemma, pos=None):
        """
        Get all inflected forms for a lemma
        
        Args:
            lemma: Greek lemma to expand
            pos: Optional part of speech filter
            
        Returns:
            Dictionary of forms organized by grammatical categories
        """
        cursor = self.conn.cursor()
        
        if pos:
            cursor.execute("""
            SELECT f.form, f.morphology
            FROM greek_lemmas l
            JOIN greek_forms f ON l.id = f.lemma_id
            WHERE l.lemma = %s AND l.part_of_speech = %s
            """, (lemma, pos))
        else:
            cursor.execute("""
            SELECT f.form, f.morphology
            FROM greek_lemmas l
            JOIN greek_forms f ON l.id = f.lemma_id
            WHERE l.lemma = %s
            """, (lemma,))
            
        results = cursor.fetchall()
        
        # Organize by grammatical categories
        organized = {}
        for form, morphology in results:
            for key, value in morphology.items():
                if key not in organized:
                    organized[key] = {}
                if value not in organized[key]:
                    organized[key][value] = []
                organized[key][value].append(form)
                
        return organized
        
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
```

**Key Considerations:**
- Implement connection pooling for multi-user environments
- Create proper caching mechanisms to improve performance
- Develop sophisticated Greek stemming algorithms
- Document the API thoroughly

## Complete Workflow Integration

To tie all the components together, create a workflow manager:

```python
def run_complete_workflow(word_list_file, output_dir, db_config):
    """
    Run the complete Greek lemmatizer workflow
    
    Args:
        word_list_file: File containing list of Greek words
        output_dir: Directory for intermediate and final output
        db_config: Database configuration
    """
    # Create necessary directories
    data_dir = os.path.join(output_dir, 'word_data')
    csv_dir = os.path.join(output_dir, 'csv')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)
    
    # Load word list
    with open(word_list_file, 'r', encoding='utf-8') as f:
        word_list = [line.strip() for line in f if line.strip()]
    
    print(f"Processing {len(word_list)} Greek words")
    
    # Step 1-3: Scrape data and extract tables
    word_data = process_greek_word_list(word_list, data_dir)
    
    # Step 4: Create CSV files
    create_csv_files(word_data, csv_dir)
    
    # Step 5: Import to database
    import_to_database(csv_dir, db_config)
    
    # Step 6: Test the lemmatizer
    lemmatizer = GreekLemmatizer(db_config)
    
    # Test a few words
    test_words = word_list[:5]
    for word in test_words:
        results = lemmatizer.lemmatize(word)
        print(f"Results for '{word}':")
        for result in results:
            print(f"  - {result['lemma']} ({result['pos']}): {result['definition']}")
            
    lemmatizer.close()
    
    print("Workflow completed successfully!")
```

This comprehensive guide should provide the technical foundation needed to implement the Greek lemmatizer workflow as outlined in the diagram.
