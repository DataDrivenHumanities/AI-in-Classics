# Greek Dictionary PostgreSQL - Quick Start

## Setup (5 minutes)

### 1. Install PostgreSQL
```bash
# macOS
brew install postgresql@14
brew services start postgresql@14
createdb greek_dictionary

# Or use Docker
docker run --name greek-postgres \
  -e POSTGRES_DB=greek_dictionary \
  -p 5432:5432 -d postgres:14
```

### 2. Install Python Dependencies
```bash
cd src/Lemmatizer-GRK
pip install psycopg2-binary sqlalchemy pandas
```

### 3. Load Data
```bash
python -m database.loader --drop
```

## Usage

### Python Script
```python
from database import DictionaryQuery

query = DictionaryQuery()

# Look up a word
verbs = query.lookup_verb("αγαπω", exact=True)
print(verbs[0].english)  # "to treat with affection, to caress, love"

# Search by English
results = query.search_by_english("love")
for verb in results['verbs']:
    print(f"{verb.fpp}: {verb.english}")

# Get stats
stats = query.get_stats()
print(f"Total verbs: {stats['verbs']}")
```

### Run Examples
```bash
cd examples
python simple_usage.py
python basic_lookup.py
python batch_processing.py
```

## Configuration

Set environment variables or create `.env`:
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=greek_dictionary
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=yourpassword
```

## Troubleshooting

**Connection failed?**
```python
from database import get_engine
engine = get_engine()
engine.connect()  # Test connection
```

**No data?**
```bash
python -m database.loader --drop
```

See `database/README.md` for complete documentation.
