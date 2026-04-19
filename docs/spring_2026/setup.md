
## INSTALL BREW
[Homebrew — The Missing Package Manager for macOS (or Linux)](https://brew.sh/)
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## POSTGRES SETUP
```
brew install postgresql@18
```
[postgre_setup](lila_setup)

```
#setup user and password
sudo -u postgres createuser --superuser root

sudo -u postgres psql -c "\password root"
```
```
./.venv/bin/python3 scripts/download_lemlat.py
```
```
createdb lemlat_db
```

### PLACE IN ENV
```
DATABASE_URL=postgresql://root:yourpassword@127.0.0.1/lemlat_db
```
### INIT
```
./.venv/bin/python3 scripts/bootstrap_latin_db.py

./.venv/bin/python3 src/Lemmatizer-LTN-LiLa/ops/import_lila_data.py

./.venv/bin/python3 src/Lemmatizer-LTN/etl/load_to_postgres.py \
  --outdir src/Lemmatizer-LTN/out \
  --truncate

./.venv/bin/python3 src/Lemmatizer-LTN-LiLa/ops/load_lemma_sentiment_map.py

./.venv/bin/python3 scripts/latin_lexicon_annotator_debug.py \
  --file src/sample_text/latin/rag_test_sample_1.txt \
  --payload-only --compact --top-k 10
```

## INSTALL AND RUN
https://docs.astral.sh/uv/getting-started/installation/
```
brew install uv
uv python install 3.12
```
```
# create venv
uv venv .venv --python 3.12

# install python deps
uv pip install --python .venv/bin/python --upgrade pip

uv pip install --python .venv/bin/python -r requirements.txt


# install frontend deps
cd src/frontend && npm install && cd ../..

# build jupyterlite
uv pip install --python .venv/bin/python -U "jupyterlite[all]"
.venv/bin/python -m jupyter lite build --output-dir src/frontend/public/jlite --force

#CLEAR PORTS 
fuser -k 5050/tcp; fuser -k 8501/tcp; fuser -k 3000/tcp

rm -rf /root/stanza_resources
ln -s /root/.cache/stanza/1.11.0/resources /root/stanza_resources

#Ollama
ollama pull llama3.1:8b
ollama pull gemma4:e4b

ollama create latin_model:1.0.0 -f models/latin_model/Modelfile
ollama create greek_model:1.0.0 -f models/greek_model/Modelfile
ollama create latin-sentiment-llama31-5class -f ./models/rag_v31_5classes/Modelfile.fiveclasses

# start servers (run each in a separate terminal)
PYTHONPATH=$(pwd)/src .venv/bin/python -m uvicorn app.server_fast:app --host 0.0.0.0 --port 5050 --reload --app-dir src


cd src/frontend && npm run dev -- -p 3000


#LEGACY
#PYTHONPATH=$(pwd) .venv/bin/streamlit run src/app/server_streamlit.py
```

```
# postive
Caelum pulchrum est.
```
