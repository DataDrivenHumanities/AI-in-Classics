# Latin Lemmatizer

A Python package for querying Latin lemmas and inflected forms from a PostgreSQL database.

## Installation

```bash
pip install psycopg[binary]
```

Set the `DATABASE_URL` environment variable to your PostgreSQL connection string.

## Usage

### Basic Usage

```python
from latin_lemmatizer import get_lemma, get_form

# Get lemma from any word
lemma = get_lemma("amavi")
print(lemma)  # {'lemma_nod': 'amo', 'lemma_diac': 'ămo', 'pos': 'verb', ...}

# Get all perfect active forms of "amo"
forms = get_form(lemma="amo", tense="perfect", voice="active")
for f in forms:
    print(f['form_diac'], f['person'], f['number'])

# Get plural forms from the same lemma as "amavi"
plural_forms = get_form(form="amavi", number="plural")
```

### Using the Client Class

```python
from latin_lemmatizer import LatinLemmatizer

# Create client with explicit DSN
client = LatinLemmatizer(dsn="postgresql://user:pass@host/db")

# Or use context manager
with LatinLemmatizer() as client:
    lemma = client.get_lemma("amo")
    forms = client.get_form(lemma="amo", tense="present")
```

## API Reference

### `get_lemma(word: str) -> Optional[Dict]`

Get lemma information from a word (lemma or inflected form).

**Parameters:**
- `word`: A Latin word (lemma or inflected form)

**Returns:**
- Dictionary with lemma information or `None` if not found

**Fields:**
- `id`: Database ID
- `lemma_code`: Lemma code from source
- `lemma_nod`: Normalized lemma (no diacritics)
- `lemma_diac`: Lemma with diacritics
- `pos`: Part of speech
- `gender`: Gender (if applicable)
- `page_url`: Source URL

### `get_form(...) -> List[Dict]`

Get inflected forms matching the specified criteria.

**Parameters:**
- `lemma`: Starting lemma (finds forms of this lemma)
- `form`: Starting form (finds other forms of the same lemma)
- `mood`: Filter by mood (`indicative`, `subjunctive`, `imperative`)
- `tense`: Filter by tense (`present`, `imperfect`, `future`, `perfect`, `pluperfect`, `future perfect`)
- `voice`: Filter by voice (`active`, `passive`, `deponent`)
- `person`: Filter by person (`first`, `second`, `third`)
- `number`: Filter by number (`singular`, `plural`)
- `gender`: Filter by gender (`masculine`, `feminine`, `neuter`)
- `case`: Filter by case (`nominative`, `genitive`, `dative`, `accusative`, `ablative`, `vocative`, `locative`)
- `degree`: Filter by degree (`positive`, `comparative`, `superlative`)
- `verb_form`: Filter by verb form (`infinitive`, `participle`, `gerund`, `gerundive`, `supine`)

**Note:** You must provide exactly one of `lemma` or `form`, but not both.

**Returns:**
- List of dictionaries with form information

**Fields:**
- `id`: Database ID
- `lemma_id`: Foreign key to lemma
- `form_nod`: Normalized form (no diacritics)
- `form_diac`: Form with diacritics
- `label`: Original label from source
- `mood`, `tense`, `voice`, `person`, `number`, `gender`, `case`, `degree`, `verb_form`: Morphological features
- `page_url`: Source URL

## Examples

```python
from latin_lemmatizer import get_lemma, get_form

# Example 1: Get the lemma of "amavi"
lemma = get_lemma("amavi")
print(f"Lemma: {lemma['lemma_diac']}")  # Output: ămo

# Example 2: Get all forms of "amo"
all_forms = get_form(lemma="amo")
print(f"Found {len(all_forms)} forms")

# Example 3: Get present indicative active forms of "amo"
present_forms = get_form(
    lemma="amo",
    mood="indicative",
    tense="present",
    voice="active"
)
for f in present_forms:
    print(f"{f['form_diac']}: {f['person']} {f['number']}")

# Example 4: Get the infinitive of "amo"
infinitive = get_form(lemma="amo", verb_form="infinitive")
print(infinitive[0]['form_diac'] if infinitive else "Not found")

# Example 5: Get accusative singular forms from the same lemma as "rosa"
acc_sg = get_form(form="rosa", case="accusative", number="singular")

# Example 6: Get passive forms from the same lemma as "amat"
passive_forms = get_form(form="amat", voice="passive")
```

## Database Schema

The package queries two tables:

### `lemmas`
- Stores dictionary headwords with part-of-speech information

### `forms`
- Stores inflected forms with morphological tags
- Linked to lemmas via `lemma_id`

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (required if not passing `dsn` to constructor)
  - Format: `postgresql://user:password@host:port/database`

