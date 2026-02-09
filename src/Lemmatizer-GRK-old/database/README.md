# Greek Dictionary PostgreSQL Integration

Complete PostgreSQL integration for the Greek Lemmatizer workflow, following the BeautifulSoup scraping approach.

## Workflow Overview

```
┌─────────────────┐
│  Scrape HTML    │
│  per page       │ (using BeautifulSoup)
│  from LSJ       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Extract Links  │
│  to Tables      │ (BeautifulSoup parsing)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Scrape Notes   │
│  per Word       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Put into CSV   │ ✓ DONE
│  Files for      │
│  persistent     │
│  storage        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Insert INTO    │ ✓ NEW: This Package
│  Relational DB  │
│  like           │
│  PostgreSQL     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Abstract       │ ✓ NEW: DictionaryQuery API
│  querying w/    │
│  Python package │
└─────────────────┘
```

## Features

- **SQLAlchemy ORM Models** - Clean object-relational mapping for Greek dictionary data
- **Automated Data Loading** - Import CSV files into PostgreSQL with a single command
- **Query Abstraction** - High-level Python API for dictionary lookups
- **Batch Operations** - Efficient bulk inserts and queries
- **Flexible Configuration** - Environment variables or direct configuration

## Installation

### 1. Install Dependencies

```bash
cd /path/to/AI-in-Classics
pip install -r requirements.txt
```

This installs:
- `psycopg2-binary` - PostgreSQL adapter
- `sqlalchemy` - ORM framework
- `pandas` - CSV processing

### 2. Set Up PostgreSQL

#### Option A: Local PostgreSQL

```bash
# Install PostgreSQL (macOS)
brew install postgresql@14
brew services start postgresql@14

# Create database
createdb greek_dictionary
```

#### Option B: Docker PostgreSQL

```bash
docker run --name greek-postgres \
  -e POSTGRES_DB=greek_dictionary \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  -d postgres:14
```

### 3. Configure Database Connection

Create `.env` file in `src/Lemmatizer-GRK/`:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=greek_dictionary
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
```

Or set environment variables:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=greek_dictionary
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=yourpassword
```

## Usage

### Loading Data from CSV

```bash
cd src/Lemmatizer-GRK

# Load all CSV data into PostgreSQL
python -m database.loader --drop

# Or specify custom data directory
python -m database.loader --data-dir /path/to/csv/files

# Custom database URL
python -m database.loader --db-url postgresql://user:pass@host:5432/dbname
```

Options:
- `--drop` - Drop existing tables before loading
- `--data-dir` - Directory containing CSV files (default: `greek_dictionary/`)
- `--db-url` - Custom PostgreSQL connection URL
- `--batch-size` - Number of records per batch (default: 1000)

### Querying the Database

#### Python API

```python
from database import DictionaryQuery

# Initialize query interface
query = DictionaryQuery()

# Get database statistics
stats = query.get_stats()
print(f"Total verbs: {stats['verbs']}")
print(f"Total nouns: {stats['nouns']}")

# Look up a verb
verbs = query.lookup_verb("αγαπω", exact=True)
for verb in verbs:
    print(f"{verb.fpp}: {verb.english}")

# Search by English translation
results = query.search_by_english("love", pos="verb")
for verb in results['verbs']:
    print(f"{verb.fpp} - {verb.english}")

# Look up word across all parts of speech
all_results = query.lookup_word("λογος")
print(f"Nouns: {len(all_results['nouns'])}")
print(f"Verbs: {len(all_results['verbs'])}")

# Get random words for testing
random_verbs = query.get_random_words(pos='verb', count=5)
for verb in random_verbs:
    print(f"{verb.fpp}: {verb.english}")

# Batch lookup
words = ["λογος", "αγαπω", "ανθρωπος"]
batch_results = query.batch_lookup(words)
for word, results in batch_results.items():
    print(f"\n{word}:")
    for pos, items in results.items():
        print(f"  {pos}: {len(items)} results")
```

#### Direct SQLAlchemy Usage

```python
from database import get_session, GreekVerb, GreekNoun

# Get session
session = get_session()

# Query verbs
verbs = session.query(GreekVerb)\
    .filter(GreekVerb.english.like('%love%'))\
    .limit(10)\
    .all()

for verb in verbs:
    print(f"{verb.fpp}: {verb.english}")

# Complex queries
from sqlalchemy import and_, or_

results = session.query(GreekNoun)\
    .filter(and_(
        GreekNoun.english.ilike('%man%'),
        GreekNoun.sentiment != None
    ))\
    .all()

session.close()
```

## Database Schema

### Tables

#### `greek_words`
Headwords scraped from LSJ dictionary.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| lemma | String(255) | Greek headword |
| url | Text | Source URL |
| source | String(50) | Dictionary source (LSJ) |
| language | String(10) | Language code (grc) |
| created_at | DateTime | Timestamp |

#### `greek_verbs`
Greek verbs with translations.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| word_id | Integer | Foreign key to greek_words |
| fpp | String(255) | First principal part |
| english | Text | English translation |
| sentiment | String(50) | Sentiment analysis |
| created_at | DateTime | Timestamp |

Similar schemas for `greek_nouns`, `greek_adjectives`, `greek_adverbs`.

#### `greek_lemmas`
Word forms with morphological information.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| text | String(255) | Word form |
| bare_text | String(255) | Normalized form |
| sequence_num | Integer | Sequence number |
| morph_code | String(50) | Morphological code |
| base_form | String(255) | Base/lemma form |
| bare_base_form | String(255) | Normalized base |
| definition | Text | Definition |
| created_at | DateTime | Timestamp |

#### `greek_parses`
Inflected forms with parsing details.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| word_id | Integer | Foreign key to greek_lemmas |
| morph_code | String(50) | Morphological code |
| text | String(255) | Inflected form |
| bare_text | String(255) | Normalized form |
| exp_text | Text | Expanded text |
| dialects | String(100) | Dialect information |
| misc_features | Text | Additional features |
| created_at | DateTime | Timestamp |

### Indexes

- `idx_lemma_language` - Composite index on (lemma, language)
- `idx_verb_fpp` - Index on verb first principal part
- `idx_noun_fpp` - Index on noun first principal part
- `idx_adjective_fpp` - Index on adjective first principal part
- `idx_adverb_fpp` - Index on adverb first principal part
- `idx_lemma_bare_text` - Index on normalized lemma text
- `idx_lemma_base_form` - Index on base form
- `idx_parse_bare_text` - Index on normalized parse text

## API Reference

### `DatabaseLoader`

Load CSV data into PostgreSQL.

```python
from database import DatabaseLoader

loader = DatabaseLoader(
    engine=None,        # SQLAlchemy engine (creates new if None)
    data_dir=None,      # CSV directory (default: greek_dictionary/)
    batch_size=1000     # Records per batch
)

# Create tables
loader.create_tables(drop_existing=False)

# Load specific parts of speech
loader.load_verbs()
loader.load_nouns()
loader.load_adjectives()
loader.load_adverbs()

# Load all data
loader.load_all(create_tables=True, drop_existing=False)
```

### `DictionaryQuery`

Query Greek dictionary data.

```python
from database import DictionaryQuery

query = DictionaryQuery(engine=None)

# Verb queries
query.lookup_verb(fpp, exact=False)
query.get_all_verbs(limit=None)

# Noun queries
query.lookup_noun(fpp, exact=False)
query.get_all_nouns(limit=None)

# Adjective queries
query.lookup_adjective(fpp, exact=False)
query.get_all_adjectives(limit=None)

# Adverb queries
query.lookup_adverb(fpp, exact=False)
query.get_all_adverbs(limit=None)

# Combined queries
query.lookup_word(text, pos=None, exact=False)
query.search_by_english(english_text, pos=None, limit=50)

# Lemma and parse queries
query.get_lemmas_by_base(base_form, exact=True)
query.get_parses_for_form(text, exact=True)

# Utilities
query.get_stats()
query.batch_lookup(words, pos=None)
query.get_random_words(pos='verb', count=10)
```

## Examples

See `examples/` directory for:
- `basic_lookup.py` - Simple dictionary lookups
- `batch_processing.py` - Processing multiple words
- `advanced_queries.py` - Complex SQLAlchemy queries
- `export_results.py` - Export query results to CSV/JSON

## Troubleshooting

### Connection Issues

```python
# Test connection
from database import get_engine

try:
    engine = get_engine()
    with engine.connect() as conn:
        print("✓ Database connection successful")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### Data Loading Errors

- **File not found**: Ensure CSV files are in `greek_dictionary/` directory
- **Encoding issues**: CSV files should be UTF-8 encoded
- **Permission denied**: Check PostgreSQL user permissions

### Performance Optimization

```python
# Use batch operations for large queries
from database import get_session, GreekVerb

session = get_session()

# Efficient: Load in chunks
query = session.query(GreekVerb)
for verb in query.yield_per(1000):
    process(verb)

# Inefficient: Load all at once
all_verbs = session.query(GreekVerb).all()  # May consume too much memory
```

## Development

### Running Tests

```bash
# Unit tests
python -m pytest tests/

# Integration tests (requires database)
python -m pytest tests/ --integration
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head
```

## Contributing

When adding new features:
1. Update models in `models.py`
2. Add loader methods in `loader.py`
3. Add query methods in `query.py`
4. Update this README
5. Add tests

## License

See parent project LICENSE.
