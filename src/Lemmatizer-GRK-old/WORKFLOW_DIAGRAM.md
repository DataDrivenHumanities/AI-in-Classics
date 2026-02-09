# Greek Lemmatizer Workflow Diagram

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐         ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│              │         │              │         │              │         │              │         │              │         │              │
│  Scrape HTML │         │Extract Lines │         │ Scrape Tables│         │ Put into CSV │         │ Insert into  │         │   Abstract   │
│  from Greek  ├────────▶│  to Tables   ├────────▶│  per Word    ├────────▶│   Files for  ├────────▶│ relational DB├────────▶│ querying w/  │
│  Wiktionary  │         │              │         │              │         │  persistent  │         │     like     │         │    Python    │
│              │         │              │         │              │         │   storage    │         │  PostgreSQL  │         │   package    │
└──────────────┘         └──────────────┘         └──────────────┘         └──────────────┘         └──────────────┘         └──────────────┘
       ▲                                                 │                        │                        │
       │                                                 │                        │                        │
       │                                                 ▼                        ▼                        ▼
┌──────────────┐                               ┌──────────────────────────────────────────────────────────────────────┐
│              │                               │                                                                      │
│    Greek     │                               │                                                                      │
│  Wiktionary  │                               │                       Data Structures                                │
│              │                               │                                                                      │
└──────────────┘                               └──────────────────────────────────────────────────────────────────────┘
                                                               │
                                                               │
                                                               ▼
                                               ┌──────────────────────────────┐
                                               │                              │
                                               │     Greek Dictionary Files   │
                                               │     - nouns.csv              │
                                               │     - verbs.csv              │
                                               │     - adjectives.csv         │
                                               │     - adverbs.csv            │
                                               │                              │
                                               └──────────────────────────────┘
```

## Workflow Process Description

1. **Scrape HTML from Greek Wiktionary**
   - Use web scraping techniques to extract Greek word entries from Wiktionary or another comprehensive Greek dictionary source
   - Process Unicode characters properly to handle Greek alphabet

2. **Extract Lines to Tables**
   - Parse the HTML content to identify relevant linguistic data
   - Extract morphological information, definitions, and part-of-speech details

3. **Scrape Tables per Word**
   - For each Greek word, extract and organize grammatical information
   - Structure data based on part of speech (noun, verb, adjective, etc.)

4. **Put into CSV Files for persistent storage**
   - Store extracted data in well-structured CSV files
   - Organize by part of speech (nouns.csv, verbs.csv, etc.)
   - Include linguistic metadata and English definitions

5. **Insert into relational DB like PostgreSQL**
   - Design database schema to efficiently store Greek lexical data
   - Import CSV data into tables with appropriate relationships
   - Implement indices for fast lookup by word forms

6. **Abstract querying with Python package**
   - Create a Python interface for lemmatization queries
   - Develop functions to convert inflected Greek word forms to dictionary entries
   - Enable morphological analysis of Greek text

This workflow provides a comprehensive process for creating a Greek lemmatizer system, similar to the Latin lemmatizer workflow shown in the reference implementation.
