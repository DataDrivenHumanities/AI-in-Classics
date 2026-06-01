-- Convenience views for LiLa/LEMLAT tables (run AFTER importing LEMLAT into schema `lila`)

-- Trim fixed-width CHAR columns from LEMLAT into clean TEXT outputs.
CREATE OR REPLACE VIEW lila.lemmario_clean AS
SELECT
    id_lemma,
    btrim(lemma) AS lemma,
    btrim(lemma_reduced) AS lemma_reduced,
    btrim(codlem) AS codlem,
    btrim(codmorf) AS codmorf,
    NULLIF(btrim(gen), '') AS gen,
    btrim(n_id) AS n_id,
    upostag,
    upostag_2,
    ts,
    src
FROM lila.lemmario;

CREATE OR REPLACE VIEW lila.analysis_clean AS
SELECT
    btrim(wf_input) AS wf_input,
    btrim(wf_analyzed) AS wf_analyzed,
    btrim(lemma) AS lemma,
    btrim(codmorf) AS codmorf,
    btrim(codlem) AS codlem,
    NULLIF(btrim(gen), '') AS gen,
    btrim(n_id) AS n_id
FROM lila.analysis;

-- Join analyses to lemma rows (when a matching lemma entry exists).
CREATE OR REPLACE VIEW lila.analysis_with_lemma AS
SELECT
    a.wf_input,
    a.wf_analyzed,
    a.lemma,
    a.codmorf,
    a.codlem,
    a.gen,
    a.n_id,
    l.id_lemma,
    l.upostag,
    l.upostag_2
FROM lila.analysis_clean a
LEFT JOIN lila.lemmario l
  ON a.lemma = l.lemma
 AND a.codmorf = l.codmorf
 AND a.codlem = l.codlem
 AND COALESCE(a.gen, '') = COALESCE(NULLIF(btrim(l.gen), ''), '')
 AND a.n_id = l.n_id;

