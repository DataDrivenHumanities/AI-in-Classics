import os
import re
import sys
import psycopg2
from psycopg2 import sql
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load .env from current directory or parents
env_path = Path(".env")
if not env_path.exists():
    # Try looking up
    for parent in Path.cwd().parents:
        if (parent / ".env").exists():
            env_path = parent / ".env"
            break
load_dotenv(env_path)

# Configuration
DATA_DIR = Path("data/lila")
OPS_DIR = Path("src/Lemmatizer-LTN-LiLa/ops")
LEMLAT_SQL_FILE = DATA_DIR / "lemlat_db.sql"
LILA_SENTIMENT_FILE = DATA_DIR / "LatinAffectusv4.tsv"
CREATE_SCHEMA_FILE = OPS_DIR / "create_lila_schema.sql"
CREATE_VIEWS_FILE = OPS_DIR / "create_lila_views.sql"

LILA_SCHEMA = os.getenv("LILA_SCHEMA", "lila")

def get_dsn():
    dsn = os.getenv("DATABASE_URL")
    print(dsn)
    if not dsn:
        # Fallback for local dev if not set
        # Try to guess or just fail prompt
        print("DATABASE_URL not set.")
        # Attempt a default?
        return "postgresql://postgres:password@127.0.0.1:5432/lemmatizer" 
    return dsn

def clean_mariadb_dump(sql_content):
    """
    Cleans a MariaDB/MySQL dump to be compatible with PostgreSQL.
    """
    lines = sql_content.splitlines()
    cleaned_lines = []
    
    in_create_table = False
    in_mysql_conditional_comment = False
    
    for line in lines:
        stripped = line.lstrip()
        lower = stripped.lower()

        # Skip multi-line MySQL "versioned" comments like:
        # /*!50001 CREATE VIEW ... */
        # which can span multiple lines (mysqldump does this for VIEWs).
        if in_mysql_conditional_comment:
            if "*/" in line:
                in_mysql_conditional_comment = False
            continue
        if stripped.startswith("/*!"):
            if "*/" not in line:
                in_mysql_conditional_comment = True
            continue

        # Skip MySQL-specific comments and settings
        if line.startswith("--") and "MariaDB" in line:
            continue
        if lower.startswith("lock tables") or lower.startswith("unlock tables"):
            continue
        # MySQL dumps include session settings that aren't valid in Postgres.
        if lower.startswith("set "):
            continue
        if lower.startswith("use "):
            continue
        if lower.startswith("create database") or lower.startswith("drop database"):
            continue
        if lower.startswith("drop table"):
            line = re.sub(r"`([^`]+)`", r'"\1"', line)
            cleaned_lines.append(line)
            continue

        # Detect CREATE TABLE start
        if lower.startswith("create table"):
            in_create_table = True
            # Remove `if not exists` if problematic (usually ok in PG)
            # Remove backticks around table name
            line = re.sub(r"`([^`]+)`", r'"\1"', line)
            cleaned_lines.append(line)
            continue
            
        # Inside CREATE TABLE
        if in_create_table:
            # Check for end of CREATE TABLE
            if line.strip().startswith(") ENGINE="):
                in_create_table = False
                cleaned_lines.append(");")
                continue
            if line.strip() == ");":
                in_create_table = False
                cleaned_lines.append(line)
                continue
            
            # Remove keys/indexes defined inside CREATE TABLE (PG doesn't support non-constraint keys inline)
            if re.match(r"\s*KEY\s+", line) or re.match(r"\s*FULLTEXT KEY\s+", line):
                continue

            # Foreign keys in the dump may reference tables that appear later in the file.
            # Postgres requires referenced tables to exist at CREATE TABLE time, so we drop
            # FK constraints during import (they can be re-added later if needed).
            if re.search(r"\bFOREIGN\s+KEY\b", line, flags=re.IGNORECASE):
                continue
            if re.search(r"\bCONSTRAINT\b.*\bFOREIGN\s+KEY\b", line, flags=re.IGNORECASE):
                continue
                
            # Clean column definitions
            # Backticks -> Double Quotes
            line = re.sub(r"`([^`]+)`", r'"\1"', line)
            
            # Types
            line = re.sub(r"\bint\(\d+\)", "INTEGER", line, flags=re.IGNORECASE)
            line = re.sub(r"\btinyint\(\d+\)", "SMALLINT", line, flags=re.IGNORECASE)
            line = re.sub(r"\bbigint\(\d+\)", "BIGINT", line, flags=re.IGNORECASE)
            line = re.sub(r"\bdouble\b", "DOUBLE PRECISION", line, flags=re.IGNORECASE)
            line = re.sub(r"\blongtext\b", "TEXT", line, flags=re.IGNORECASE)
            line = re.sub(r"\bmediumtext\b", "TEXT", line, flags=re.IGNORECASE)
            line = re.sub(r"\btinytext\b", "TEXT", line, flags=re.IGNORECASE)
            
            # Remove MySQL specific column attributes
            line = re.sub(r"CHARACTER SET [a-zA-Z0-9_]+", "", line, flags=re.IGNORECASE)
            line = re.sub(r"COLLATE [a-zA-Z0-9_]+", "", line, flags=re.IGNORECASE)
            line = re.sub(r"\bunsigned\b", "", line, flags=re.IGNORECASE)
            line = re.sub(r"\bzerofill\b", "", line, flags=re.IGNORECASE)
            
            # Replace UNIQUE KEY "name" with UNIQUE
            # Handles quoted identifiers
            line = re.sub(r"UNIQUE KEY\s+\"[^\"]+\"\s*\(", "UNIQUE (", line, flags=re.IGNORECASE)
            # Handles unquoted identifiers if any remained (unlikely but safe)
            line = re.sub(r"UNIQUE KEY\s+[a-zA-Z0-9_]+\s*\(", "UNIQUE (", line, flags=re.IGNORECASE)
            # Fallback for just UNIQUE KEY
            line = re.sub(r"UNIQUE KEY", "UNIQUE", line, flags=re.IGNORECASE)
            
            # Auto Increment
            line = re.sub(r"AUTO_INCREMENT", "GENERATED BY DEFAULT AS IDENTITY", line, flags=re.IGNORECASE)
            # Normalize the common "NOT NULL GENERATED ..." ordering into valid PG syntax.
            line = re.sub(
                r"\b(INTEGER|BIGINT|SMALLINT)\s+NOT\s+NULL\s+GENERATED\s+BY\s+DEFAULT\s+AS\s+IDENTITY\b",
                r"\1 GENERATED BY DEFAULT AS IDENTITY NOT NULL",
                line,
                flags=re.IGNORECASE,
            )
            
            # Timestamp fix (MySQL specific ON UPDATE)
            if "timestamp" in line.lower():
                 line = re.sub(r"ON UPDATECURRENT_TIMESTAMP\(\)", "", line, flags=re.IGNORECASE)
                 line = re.sub(r"ON UPDATE current_timestamp\(\)", "", line, flags=re.IGNORECASE)
                 line = re.sub(r"current_timestamp\(\)", "NOW()", line, flags=re.IGNORECASE)
            
            # Remove trailing comma if it was before a skipped KEY
            # (We'll fix trailing commas later or just hope the last col doesn't have one)
            
            cleaned_lines.append(line)
        else:
            # INSERT statements
            if lower.startswith("insert into"):
                line = re.sub(r"`([^`]+)`", r'"\1"', line)
                # MySQL uses \' escape, PG uses ''
                # This is tricky without a proper parser. 
                # Hopefully the dump uses standard SQL values.
                # If they use \' for apostrophes, we might have issues.
                # Let's simple-replace \' with '' if it looks like text escape
                # (This is risky but usually necessary for MySQL->PG)
                line = line.replace("\\'", "''") 
                cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)

    # Post-process to fix trailing commas in CREATE TABLE
    # A generic regex approach: find `,\s*\);` and replace with `\n);`
    full_sql = "\n".join(cleaned_lines)
    # This is a bit brute force. 
    # Better: execute statement by statement, PG might complain about trailing comma.
    # Postgres 11+ is stricter.
    # Let's try to remove trailing commas before );
    full_sql = re.sub(r",(\s*\);)", r"\1", full_sql)

    # Final safety: if any backticks survived cleaning, convert them to double-quotes.
    full_sql = full_sql.replace("`", '"')
    
    return full_sql

def ensure_schema(conn, schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema))
        )
    conn.commit()

def set_search_path(conn, schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema))
        )
    conn.commit()

def import_lemlat(conn):
    print(f"Reading {LEMLAT_SQL_FILE}...")
    with open(LEMLAT_SQL_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    print("Cleaning SQL for PostgreSQL...")
    cleaned_sql = clean_mariadb_dump(content)
    
    print("Executing LEMLAT SQL...")
    with conn.cursor() as cur:
        # Execute in one go? It might be large.
        # But split by ; might break inside strings.
        # psycopg2 can execute scripts using executescript-like behavior?
        # No, execute() handles multiple statements.
        try:
            cur.execute(cleaned_sql)
            conn.commit()
            print("LEMLAT data imported successfully.")
        except Exception as e:
            conn.rollback()
            print(f"Error importing LEMLAT SQL: {e}")
            # Identify the error line?
            # Save the cleaned SQL for debugging
            with open(OPS_DIR / "lemlat_pg_debug.sql", "w") as f:
                f.write(cleaned_sql)
            print(f"Saved cleaned SQL to {OPS_DIR / 'lemlat_pg_debug.sql'} for inspection.")
            raise

def create_lila_schema(conn):
    print(f"Executing {CREATE_SCHEMA_FILE}...")
    with open(CREATE_SCHEMA_FILE, "r") as f:
        sql_content = f.read()
    with conn.cursor() as cur:
        cur.execute(sql_content)
        conn.commit()
    print("LiLa schema objects created.")

def create_lila_views(conn):
    print(f"Executing {CREATE_VIEWS_FILE}...")
    with open(CREATE_VIEWS_FILE, "r") as f:
        sql_content = f.read()
    with conn.cursor() as cur:
        cur.execute(sql_content)
        conn.commit()
    print("LiLa views created.")

def import_sentiment_data(conn):
    print(f"Importing {LILA_SENTIMENT_FILE}...")
    df = pd.read_csv(LILA_SENTIMENT_FILE, sep="\t")
    
    # Check columns
    required_cols = {"lemma", "pos", "polarity_score", "has_polarity", "provenance"}
    if not required_cols.issubset(df.columns):
        print(f"Warning: Columns mismatch. Found: {df.columns}")
    
    # Insert data
    # Using execute_batch for performance
    from psycopg2.extras import execute_batch
    
    insert_sql = """
    INSERT INTO lila.sentiment (lemma, pos, polarity_score, has_polarity, provenance)
    VALUES (%s, %s, %s, %s, %s)
    """
    
    data = []
    for _, row in df.iterrows():
        # Clean/convert types if needed
        score = row.get("polarity_score")
        if pd.isna(score): score = None
        data.append((
            row.get("lemma"),
            row.get("pos"),
            score,
            row.get("has_polarity"),
            row.get("provenance")
        ))
        
    with conn.cursor() as cur:
        # Keep this import idempotent (re-running the script shouldn't duplicate rows).
        cur.execute("TRUNCATE TABLE lila.sentiment;")
        execute_batch(cur, insert_sql, data)
        conn.commit()
    print(f"Imported {len(data)} sentiment records.")

def main():
    dsn = get_dsn()
    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(dsn)
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)
        
    try:
        ensure_schema(conn, LILA_SCHEMA)
        set_search_path(conn, LILA_SCHEMA)

        # 1. Import LEMLAT
        # Check if tables already exist? 
        # For now, we assume a fresh import or overwrite.
        # The cleaned SQL has DROP TABLE IF EXISTS usually? 
        # The original dump had DROP TABLE IF EXISTS.
        import_lemlat(conn)
        
        # 2. Create sentiment table + indexes
        create_lila_schema(conn)
        
        # 3. Import Sentiment Data
        import_sentiment_data(conn)

        # 4. Create convenience views over imported LEMLAT tables
        create_lila_views(conn)
        
        print("Phase 1 Import Complete!")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
