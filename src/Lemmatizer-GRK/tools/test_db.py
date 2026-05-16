import psycopg
import unicodedata

# Your local Docker Database URL
DSN = "postgresql://postgres:mysecretpassword@localhost:5432/greek_lemmatizer"

def strip_accents(text):
    """Removes Greek accents to match database storage."""
    if not text: return ""
    normalized = unicodedata.normalize('NFD', text)
    return "".join(c for c in normalized if unicodedata.category(c) != 'Mn')

def main():
    print("🔍 Testing Greek Lemmatizer Database...\n")
    
    # 💡 TIP: If these specific words aren't in the batch of 10 pages you scraped, 
    # open your 'out/' folder, pick a Greek word from one of the CSVs, and type it here!
    test_words = ["λόγος", "εἰμί", "λύω"] 

    try:
        with psycopg.connect(DSN) as conn:
            with conn.cursor() as cur:
                
                for word in test_words:
                    print(f"--- Testing Form: '{word}' ---")
                    word_nod = strip_accents(word)
                    
                    # 1. Find the parent Dictionary entry (Lemma) using standard SQL
                    cur.execute("""
                        SELECT DISTINCT l.lemma_diac, l.pos 
                        FROM lemmas l
                        JOIN forms f ON l.id = f.lemma_id
                        WHERE f.form_nod = %s OR l.lemma_nod = %s;
                    """, (word_nod, word_nod))
                    
                    lemma_result = cur.fetchone()
                    
                    if lemma_result:
                        print(f"📖 Dictionary Entry: {lemma_result[0]}")
                        print(f"🏷️  Part of Speech:   {lemma_result[1]}")
                    else:
                        print(f"⚠️ Could not find dictionary entry for '{word}'.")
                        print("\n")
                        continue # Skip checking grammar if the word doesn't exist
                    
                    # 2. Get the specific grammatical breakdown
                    cur.execute("""
                        SELECT f.form_diac, f.tense, f.voice, f.mood, f."case", f.number, f.gender
                        FROM forms f
                        JOIN lemmas l ON f.lemma_id = l.id
                        WHERE f.form_nod = %s;
                    """, (word_nod,))
                    
                    grammar_results = cur.fetchall()
                    
                    if grammar_results:
                        print("⚙️  Grammatical Parsings Found:")
                        for r in grammar_results:
                            # Filter out empty columns so the printout looks clean
                            parsing = [str(item) for item in r[1:] if item] 
                            print(f"   ➔ {r[0]}: {', '.join(parsing).title()}")
                    else:
                        print("⚠️ No grammatical parsings found.")
                    
                    print("\n")
                    
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    main()