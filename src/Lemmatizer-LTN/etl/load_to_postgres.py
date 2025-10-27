import argparse, csv, psycopg

p = argparse.ArgumentParser()
p.add_argument("--db", required=True)
p.add_argument("--lemmas", required=True)
p.add_argument("--forms", required=True)
a = p.parse_args()

def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, None)  # allow empty files with header only
        return header, [tuple(row) for row in r]

with psycopg.connect(a.db) as conn, conn.cursor() as cur:
    # Create schema (idempotent) already done in pipeline; harmless if run again
    # Upsert lemmas
    _, lrows = read_csv(a.lemmas)
    if lrows:
        cur.executemany("""
            INSERT INTO lemmas (lemma_code,lemma_nod,lemma_diac,pos,gender,page_url)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (lemma_nod) DO UPDATE SET
              lemma_code=EXCLUDED.lemma_code, lemma_diac=EXCLUDED.lemma_diac,
              pos=EXCLUDED.pos, gender=EXCLUDED.gender, page_url=EXCLUDED.page_url
        """, lrows)

    # Insert forms (resolve lemma_id by lemma_nod; skip if no rows)
    _, frows = read_csv(a.forms)
    for r in frows:
        (lemma_nod, form_nod, form_diac, label, mood, tense, voice,
         person, number, gender, case, degree, page_url) = r
        cur.execute("SELECT id FROM lemmas WHERE lemma_nod = norm(%s)", (lemma_nod,))
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO lemmas (lemma_nod) VALUES (norm(%s)) RETURNING id", (lemma_nod,))
            lemma_id = cur.fetchone()[0]
        else:
            lemma_id = row[0]
        cur.execute("""
          INSERT INTO forms (lemma_id,form_nod,form_diac,label,mood,tense,voice,person,number,gender,"case",degree,page_url)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
          ON CONFLICT DO NOTHING
        """, (lemma_id, form_nod, form_diac, label, mood, tense, voice, person, number, gender, case, degree, page_url))
    conn.commit()

print("Load complete.")
