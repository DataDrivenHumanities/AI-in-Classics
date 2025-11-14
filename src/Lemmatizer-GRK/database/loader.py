"""
Database Loader

Imports Greek dictionary data from CSV files into PostgreSQL.
Handles:
- Greek words (headwords from LSJ)
- Part-of-speech specific data (verbs, nouns, adjectives, adverbs)
- Lemmas and parses (morphological data)
"""

import os
import csv
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from .config import get_engine, get_session
from .models import (
    Base, GreekWord, GreekVerb, GreekNoun, 
    GreekAdjective, GreekAdverb, GreekLemma, GreekParse, PerseusVocabLemma
)


class DatabaseLoader:
    """
    Load Greek dictionary data from CSV files into PostgreSQL.
    """
    
    def __init__(
        self, 
        engine: Optional[Engine] = None,
        data_dir: Optional[str] = None,
        batch_size: int = 1000
    ):
        """
        Initialize loader.
        
        Args:
            engine: SQLAlchemy engine (creates new if None)
            data_dir: Directory containing CSV files (defaults to greek_dictionary/)
            batch_size: Number of records to insert per batch
        """
        self.engine = engine or get_engine()
        self.batch_size = batch_size
        
        if data_dir is None:
            # Default to greek_dictionary directory relative to this file
            current_dir = Path(__file__).parent.parent
            self.data_dir = current_dir / 'greek_dictionary'
        else:
            self.data_dir = Path(data_dir)
    
    def create_tables(self, drop_existing: bool = False):
        """
        Create database tables.
        
        Args:
            drop_existing: If True, drop existing tables first
        """
        if drop_existing:
            print("Dropping existing tables...")
            Base.metadata.drop_all(self.engine)
        
        print("Creating database tables...")
        Base.metadata.create_all(self.engine)
        print("✓ Tables created successfully")
    
    def load_verbs(self, csv_path: Optional[str] = None) -> int:
        """
        Load Greek verbs from CSV.
        
        Args:
            csv_path: Path to verbs.csv (defaults to data_dir/verbs.csv)
            
        Returns:
            Number of records loaded
        """
        if csv_path is None:
            csv_path = self.data_dir / 'verbs.csv'
        
        print(f"Loading verbs from {csv_path}...")
        
        try:
            df = pd.read_csv(csv_path, sep='\t' if '\t' in open(csv_path).read(1024) else ',')
        except Exception:
            df = pd.read_csv(csv_path)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Map column names (handle potential variations)
        if 'FPP' not in df.columns and df.columns[0] != 'FPP':
            # Skip first column if it's an index
            if df.columns[0] in ['', 'Unnamed: 0']:
                df = df.iloc[:, 1:]
        
        session = get_session(self.engine)
        count = 0
        
        try:
            records = []
            for _, row in df.iterrows():
                verb = GreekVerb(
                    fpp=str(row.get('FPP', row.iloc[0])).strip(),
                    english=str(row.get('English', row.iloc[1])) if pd.notna(row.get('English', row.iloc[1])) else None,
                    sentiment=str(row.get('Sentiment', row.iloc[2])) if pd.notna(row.get('Sentiment', row.iloc[2])) and str(row.get('Sentiment', row.iloc[2])) != 'NULL' else None
                )
                records.append(verb)
                
                if len(records) >= self.batch_size:
                    session.bulk_save_objects(records)
                    session.commit()
                    count += len(records)
                    print(f"  Loaded {count} verbs...")
                    records = []
            
            if records:
                session.bulk_save_objects(records)
                session.commit()
                count += len(records)
            
            print(f"✓ Loaded {count} verbs")
            return count
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error loading verbs: {e}", file=sys.stderr)
            raise
        finally:
            session.close()
    
    def load_nouns(self, csv_path: Optional[str] = None) -> int:
        """Load Greek nouns from CSV."""
        if csv_path is None:
            csv_path = self.data_dir / 'nouns.csv'
        
        print(f"Loading nouns from {csv_path}...")
        
        try:
            df = pd.read_csv(csv_path, sep='\t' if '\t' in open(csv_path).read(1024) else ',')
        except Exception:
            df = pd.read_csv(csv_path)
        
        df.columns = df.columns.str.strip()
        
        if df.columns[0] in ['', 'Unnamed: 0']:
            df = df.iloc[:, 1:]
        
        session = get_session(self.engine)
        count = 0
        
        try:
            records = []
            for _, row in df.iterrows():
                noun = GreekNoun(
                    fpp=str(row.get('FPP', row.iloc[0])).strip(),
                    english=str(row.get('English', row.iloc[1])) if pd.notna(row.get('English', row.iloc[1])) else None,
                    sentiment=str(row.get('Sentiment', row.iloc[2])) if pd.notna(row.get('Sentiment', row.iloc[2])) and str(row.get('Sentiment', row.iloc[2])) != 'NULL' else None
                )
                records.append(noun)
                
                if len(records) >= self.batch_size:
                    session.bulk_save_objects(records)
                    session.commit()
                    count += len(records)
                    print(f"  Loaded {count} nouns...")
                    records = []
            
            if records:
                session.bulk_save_objects(records)
                session.commit()
                count += len(records)
            
            print(f"✓ Loaded {count} nouns")
            return count
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error loading nouns: {e}", file=sys.stderr)
            raise
        finally:
            session.close()
    
    def load_adjectives(self, csv_path: Optional[str] = None) -> int:
        """Load Greek adjectives from CSV."""
        if csv_path is None:
            csv_path = self.data_dir / 'adjectives.csv'
        
        print(f"Loading adjectives from {csv_path}...")
        
        try:
            df = pd.read_csv(csv_path, sep='\t' if '\t' in open(csv_path).read(1024) else ',')
        except Exception:
            df = pd.read_csv(csv_path)
        
        df.columns = df.columns.str.strip()
        
        if df.columns[0] in ['', 'Unnamed: 0']:
            df = df.iloc[:, 1:]
        
        session = get_session(self.engine)
        count = 0
        
        try:
            records = []
            for _, row in df.iterrows():
                adj = GreekAdjective(
                    fpp=str(row.get('FPP', row.iloc[0])).strip(),
                    english=str(row.get('English', row.iloc[1])) if pd.notna(row.get('English', row.iloc[1])) else None,
                    sentiment=str(row.get('Sentiment', row.iloc[2])) if pd.notna(row.get('Sentiment', row.iloc[2])) and str(row.get('Sentiment', row.iloc[2])) != 'NULL' else None
                )
                records.append(adj)
                
                if len(records) >= self.batch_size:
                    session.bulk_save_objects(records)
                    session.commit()
                    count += len(records)
                    print(f"  Loaded {count} adjectives...")
                    records = []
            
            if records:
                session.bulk_save_objects(records)
                session.commit()
                count += len(records)
            
            print(f"✓ Loaded {count} adjectives")
            return count
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error loading adjectives: {e}", file=sys.stderr)
            raise
        finally:
            session.close()
    
    def load_adverbs(self, csv_path: Optional[str] = None) -> int:
        """Load Greek adverbs from CSV."""
        if csv_path is None:
            csv_path = self.data_dir / 'adverbs.csv'
        
        print(f"Loading adverbs from {csv_path}...")
        
        try:
            df = pd.read_csv(csv_path, sep='\t' if '\t' in open(csv_path).read(1024) else ',')
        except Exception:
            df = pd.read_csv(csv_path)
        
        df.columns = df.columns.str.strip()
        
        if df.columns[0] in ['', 'Unnamed: 0']:
            df = df.iloc[:, 1:]
        
        session = get_session(self.engine)
        count = 0
        
        try:
            records = []
            for _, row in df.iterrows():
                adv = GreekAdverb(
                    fpp=str(row.get('FPP', row.iloc[0])).strip(),
                    english=str(row.get('English', row.iloc[1])) if pd.notna(row.get('English', row.iloc[1])) else None,
                    sentiment=str(row.get('Sentiment', row.iloc[2])) if pd.notna(row.get('Sentiment', row.iloc[2])) and str(row.get('Sentiment', row.iloc[2])) != 'NULL' else None
                )
                records.append(adv)
                
                if len(records) >= self.batch_size:
                    session.bulk_save_objects(records)
                    session.commit()
                    count += len(records)
                    print(f"  Loaded {count} adverbs...")
                    records = []
            
            if records:
                session.bulk_save_objects(records)
                session.commit()
                count += len(records)
            
            print(f"✓ Loaded {count} adverbs")
            return count
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error loading adverbs: {e}", file=sys.stderr)
            raise
        finally:
            session.close()
    
    def load_perseus_vocab(self, csv_path: Optional[str] = None) -> int:
        """
        Load Perseus vocabulary lemmas from CSV.
        
        Args:
            csv_path: Path to perseus_vocab.csv (defaults to database/perseus_vocab.csv)
            
        Returns:
            Number of records loaded
        """
        if csv_path is None:
            csv_path = self.data_dir.parent / 'database' / 'perseus_vocab.csv'
        
        print(f"Loading Perseus vocabulary from {csv_path}...")
        
        if not Path(csv_path).exists():
            print(f"⚠ File not found: {csv_path}")
            return 0
        
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"Error reading CSV: {e}", file=sys.stderr)
            return 0
        
        df.columns = df.columns.str.strip()
        
        session = get_session(self.engine)
        count = 0
        
        try:
            records = []
            for _, row in df.iterrows():
                lemma = PerseusVocabLemma(
                    lemma=str(row.get('lemma', '')).strip(),
                    lemma_id=str(row.get('lemma_id')) if pd.notna(row.get('lemma_id')) else None,
                    atlas_id=str(row.get('atlas_id')) if pd.notna(row.get('atlas_id')) else None,
                    url=str(row.get('url')) if pd.notna(row.get('url')) else None,
                    source=str(row.get('source', 'perseus')),
                    language=str(row.get('language', 'grc')),
                    corpus_count=int(row.get('corpus_count')) if pd.notna(row.get('corpus_count')) else None,
                    corpus_freq=float(row.get('corpus_freq')) if pd.notna(row.get('corpus_freq')) else None,
                    core_count=int(row.get('core_count')) if pd.notna(row.get('core_count')) else None,
                    core_freq=float(row.get('core_freq')) if pd.notna(row.get('core_freq')) else None,
                    definition=str(row.get('definition')) if pd.notna(row.get('definition')) else None,
                    gloss=str(row.get('gloss')) if pd.notna(row.get('gloss')) else None
                )
                records.append(lemma)
                
                if len(records) >= self.batch_size:
                    session.bulk_save_objects(records)
                    session.commit()
                    count += len(records)
                    print(f"  Loaded {count} Perseus lemmas...")
                    records = []
            
            if records:
                session.bulk_save_objects(records)
                session.commit()
                count += len(records)
            
            print(f"✓ Loaded {count} Perseus vocabulary lemmas")
            return count
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error loading Perseus vocabulary: {e}", file=sys.stderr)
            raise
        finally:
            session.close()
    
    def load_all(self, create_tables: bool = True, drop_existing: bool = False):
        """
        Load all CSV data into database.
        
        Args:
            create_tables: Whether to create tables first
            drop_existing: Whether to drop existing tables
        """
        if create_tables:
            self.create_tables(drop_existing=drop_existing)
        
        print("\n" + "="*60)
        print("Loading Greek Dictionary Data into PostgreSQL")
        print("="*60 + "\n")
        
        total = 0
        
        # Load part-of-speech data
        files = [
            ('verbs', self.load_verbs),
            ('nouns', self.load_nouns),
            ('adjectives', self.load_adjectives),
            ('adverbs', self.load_adverbs),
            ('perseus_vocab', self.load_perseus_vocab),
        ]
        
        for name, loader_func in files:
            try:
                count = loader_func()
                total += count
            except FileNotFoundError:
                print(f"⚠ Skipping {name}: file not found")
            except Exception as e:
                print(f"✗ Error loading {name}: {e}")
        
        print("\n" + "="*60)
        print(f"Total records loaded: {total}")
        print("="*60 + "\n")
        
        return total


def main():
    """CLI entry point for data loading."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load Greek dictionary CSV data into PostgreSQL')
    parser.add_argument('--data-dir', help='Directory containing CSV files')
    parser.add_argument('--drop', action='store_true', help='Drop existing tables before loading')
    parser.add_argument('--db-url', help='PostgreSQL connection URL')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for inserts')
    
    args = parser.parse_args()
    
    # Create engine with custom URL if provided
    engine = None
    if args.db_url:
        from sqlalchemy import create_engine
        engine = create_engine(args.db_url)
    
    # Create loader and load data
    loader = DatabaseLoader(
        engine=engine,
        data_dir=args.data_dir,
        batch_size=args.batch_size
    )
    
    try:
        loader.load_all(create_tables=True, drop_existing=args.drop)
        print("✓ Data loading completed successfully!")
        return 0
    except Exception as e:
        print(f"✗ Data loading failed: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
