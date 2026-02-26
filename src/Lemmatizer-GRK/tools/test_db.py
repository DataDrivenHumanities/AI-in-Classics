import psycopg

# Connection string to your local Docker database
DSN = "postgresql://postgres:mysecretpassword@localhost:5432/greek_lemmatizer"

def main():
    print("🔍 Connecting to the Greek Lemmatizer Database...\n")
    
    # Words to test (you can change these to words you know are in your CSV)
    # Notice we are using a mix of accented and unaccented words to test the norm() function
    test_words = ["λόγους", "λυω", "τὴν"]

    try:
        with psycopg.connect(DSN) as conn:
            with conn.cursor() as cur:
                
                for word in test_words:
                    print(f"--- Testing Form: '{word}' ---")
                    
                    # 1. Test finding the Lemma (Dictionary Word)
                    # We use the custom SQL function we built: get_lemma_by_form()
                    cur.execute("SELECT lemma_diac, english_definition FROM get_lemma_by_form(%s);", (word,))
                    lemma_result = cur.fetchone()
                    
                    if lemma_result:
                        print(f"📖 Dictionary Entry: {lemma_result[0]}")
                        print(f"🇬🇧 Definition:       {lemma_result[1]}")
                    else:
                        print(f"⚠️ Could not find dictionary entry for '{word}'.")
                    
                    # 2. Test getting the Granular Grammar Parsing
                    # We join the forms and lemmas table to see exactly what this word means
                    cur.execute("""
                        SELECT f.form_diac, f.pos, f.tense, f.voice, f.mood, f."case", f.number, f.gender
                        FROM forms f
                        JOIN lemmas l ON f.lemma_id = l.id
                        WHERE f.form_nod = norm(%s);
                    """, (word,))
                    
                    grammar_results = cur.fetchall()
                    
                    if grammar_results:
                        print("⚙️  Grammatical Parsings Found:")
                        for r in grammar_results:
                            # Filter out empty columns for a clean printout
                            parsing = [str(item) for item in r[1:] if item] 
                            print(f"   ➔ {r[0]}: {', '.join(parsing).title()}")
                    else:
                        print("⚠️ No grammatical parsings found.")
                    
                    print("\n")
                    
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   (Make sure your Docker container is running!)")

if __name__ == "__main__":
    main()