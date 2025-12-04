# Codex-Continuum
OCR tool that translates incomplete or damaged Latin transcripts into English while auto filling missing characters and words.

## Getting Started

### Step 1: Start the UI

```bash
cd frontend
npm run build
npm run dev
```

Visit the provided localhost URL (usually `http://localhost:5173`) and ensure the frontend hits `http://localhost:8000/ocr` once you have completed step 3.

### Step 2: Get your API key

Navigate to https://console.groq.com/keys where you can generate a free API key. Create an API key and copy that key. 

### Step 3: Run the OCR Service

_In WSL:_

```bash
cd Codex-Continuum-main/backend/ocr_service
```

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt 
```

Set the Groq API key:

```bash
export GROQAPIKEY="gsk_your_real_key_here"
```

Run the backend:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Testing & Coverage

We use pytest with coverage. Run everything from the project root (with your virtualenv activated).

First-time setup:

```bash
python -m pip install -U pip
python -m pip install -r backend/ocr_service/requirements.txt
python -m pip install pytest pytest-cov
```

Run tests with coverage (using the configured pytest.ini):

```bash
python -m pytest
```

The command above generates a line-by-line coverage report for the backend components under `backend/completion`, `backend/ocr_service`, and `backend/translation`.

