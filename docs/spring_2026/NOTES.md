RAG

```
rm -rf /root/stanza_resources
ln -s /root/.cache/stanza/1.11.0/resources /root/stanza_resources
```

```
ollama create latin-sentiment-llama31-5class -f ./models/rag_v31_5classes/Modelfile.fiveclasses
```

CLEAR PORTS
```
fuser -k 8501/tcp; fuser -k 5050/tcp; fuser -k 3000/tcp
```
```
@(8501, 5050, 3000) | ForEach-Object { Get-NetTCPConnection -LocalPort $_ -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }
```

LINUX
```
# create venv
uv venv .venv

# install python deps
uv pip install --python .venv/bin/python --upgrade pip
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python "fastapi>=0.110" "uvicorn[standard]>=0.23" "pydantic>=2"

# install frontend deps
cd src/frontend && npm install && cd ../..

# build jupyterlite
uv pip install --python .venv/bin/python -U "jupyterlite[all]"
.venv/bin/python -m jupyter lite build --output-dir src/frontend/public/jlite --force

# clear ports
fuser -k 5050/tcp; fuser -k 8501/tcp; fuser -k 3000/tcp

# start servers (run each in a separate terminal)
PYTHONPATH=$(pwd)/src .venv/bin/python -m uvicorn app.server_fast:app --host 0.0.0.0 --port 5050 --reload --app-dir src
PYTHONPATH=$(pwd) .venv/bin/streamlit run src/app/server_streamlit.py
cd src/frontend && npm run dev -- -p 3000
```

WINDOWS
```
# create venv
uv venv .venv

# install python deps
uv pip install --python .venv\Scripts\python.exe --upgrade pip
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip install --python .venv\Scripts\python.exe "fastapi>=0.110" "uvicorn[standard]>=0.23" "pydantic>=2"

# install frontend deps
cd src/frontend; npm install; cd ../..

# build jupyterlite
uv pip install --python .venv\Scripts\python.exe -U "jupyterlite[all]"
.venv\Scripts\python.exe -m jupyter lite build --output-dir src/frontend/public/jlite --force

# clear ports
@(5050, 8501, 3000) | ForEach-Object { Get-NetTCPConnection -LocalPort $_ -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }

# start servers (run each in a separate terminal)
$env:PYTHONPATH="$PWD\src"; .venv\Scripts\python.exe -m uvicorn app.server_fast:app --host 0.0.0.0 --port 5050 --reload --app-dir src
.venv\Scripts\python.exe -m streamlit run src/app/server_streamlit.py
cd src/frontend; npm run dev -- -p 3000
```