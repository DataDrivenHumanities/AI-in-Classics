# Quick Start

Follow these steps to get started quickly:

1. **Install Ollama**: [Download here](https://ollama.ai/download)
2. **Pull Base Model**:
   ```bash
   ollama pull llama3.1:8b-instruct
   ```
3. **Create Model**:
   ```bash
   cd models/latin_model
   ollama create latin-sentiment -f Modelfile
   ```
4. **Run Model**:
   ```bash
   ollama run latin-sentiment
   ```

For full accuracy (70%+), see [Option 2](#option-2-full-model-with-fine-tuned-adapter).


# Table of Contents
- [Quick Start](#quick-start)
- [Option 1: Quick Demo (Base Model)](#option-1-quick-demo-base-model)
- [Option 2: Full Model (With Fine-tuned Adapter)](#option-2-full-model-with-fine-tuned-adapter)
- [Using the Model](#using-the-model)
- [Enhanced Accuracy with Intensity Rules](#enhanced-accuracy-with-intensity-rules)
- [Troubleshooting](#troubleshooting)
- [File Sizes](#file-sizes)
- [Performance Comparison](#performance-comparison)
- [Complete Script](#complete-script)
- [Support](#support)


# Running Latin Sentiment Model Locally with Ollama

This guide shows you how to run Team Trojan Parse's Latin sentiment model on your own computer using Ollama.

**Two options:**
1. **Quick Demo** (5 minutes): Use base model with our prompt
2. **Full Model** (30 minutes): Convert our fine-tuned adapter for 70%+ accuracy

---

## Option 1: Quick Demo (Base Model)

### Prerequisites
- Install [Ollama](https://ollama.ai/download)
- 8GB+ RAM

### Steps

1. **Pull base model:**
```bash
ollama pull llama3.1:8b-instruct
```

2. **Create model from our Modelfile:**
```bash
cd models/latin_model
ollama create latin-sentiment -f Modelfile
```

3. **Test it:**
```bash
ollama run latin-sentiment
```

Then type:
```
Victoria splendidissima! Dux gloriam aeternam meruit!
```

**Expected output:** Classification like "VERY POSITIVE" or "EXTREMELY POSITIVE"

**Accuracy:** ~40-50% (base model with optimized prompt)

---

## Option 2: Full Model (With Fine-tuned Adapter)

For 70%+ accuracy, convert our HuggingFace adapter to GGUF format.

### Prerequisites
**LoRA Adapter:** Hosted on Hugging Face → [TronCodes/augustulus-latin-sentiment-lora](https://huggingface.co/TronCodes/augustulus-latin-sentiment-lora)

### Prerequisites

- Python 3.10+
- 16GB+ RAM
- 20GB free disk space
- CUDA GPU (optional, for faster conversion)

### Installation

1. **Install Python dependencies:**
```bash
pip install torch transformers peft accelerate sentencepiece protobuf
```

2. **Clone llama.cpp (for GGUF conversion):**
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
pip install -r requirements.txt
cd ..
```

3. **Install Ollama:**
- Download from https://ollama.ai/download
- Install for your OS (Windows/Mac/Linux)

### Step-by-Step Conversion

#### Step 1: Download and Merge Model

Create a Python script `convert_latin_model.py`:

```python
"""
Convert Team Trojan Parse Latin sentiment model to GGUF
Run this once to prepare the model for Ollama
"""
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

print("="*70)
print("Converting Latin Sentiment Model to GGUF")
print("="*70)

# Step 1: Load base model
print("\\n[1/4] Loading base Llama model...")
print("This will download ~16GB (first time only)")

base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)
print("✓ Base model loaded")

# Step 2: Load our fine-tuned adapter from HuggingFace
print("\\n[2/4] Loading Team Trojan Parse adapter...")
print("From: TronCodes/augustulus-latin-sentiment-lora")

model = PeftModel.from_pretrained(
    base_model,
    "TronCodes/augustulus-latin-sentiment-lora"
)
print("✓ Adapter loaded")

# Step 3: Merge adapter into base model
print("\\n[3/4] Merging adapter into base model...")
print("(This creates a single model with our training)")

merged_model = model.merge_and_unload()
print("✓ Merged successfully")

# Step 4: Save merged model
print("\\n[4/4] Saving merged model...")
output_dir = "./latin_sentiment_merged"

merged_model.save_pretrained(output_dir, safe_serialization=True)

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
tokenizer.save_pretrained(output_dir)

print(f"✓ Saved to: {output_dir}")
print("\\n" + "="*70)
print("Merge complete! Next: Convert to GGUF")
print("="*70)
```

**Run it:**
```bash
python convert_latin_model.py
```

**Time:** 10-15 minutes  
**Output:** `./latin_sentiment_merged/` directory with merged model

#### Step 2: Convert to GGUF Format

```bash
# Navigate to llama.cpp directory
cd llama.cpp

# Convert to GGUF (8-bit quantization for good quality/size balance)
python convert-hf-to-gguf.py \\
    ../latin_sentiment_merged \\
    --outfile ../latin_sentiment_q8_0.gguf \\
    --outtype q8_0

cd ..
```

**Options for `--outtype`:**
- `q8_0`: 8-bit (recommended) - ~8GB, best quality
- `q5_k_m`: 5-bit - ~5GB, good quality
- `q4_k_m`: 4-bit - ~4GB, acceptable quality

**Time:** 5-10 minutes  
**Output:** `latin_sentiment_q8_0.gguf` (~8GB file)

#### Step 3: Create Ollama Model

Create `Modelfile.finetuned`:

```dockerfile
# Trojan Parse - Fine-tuned Latin Sentiment Model
FROM ./latin_sentiment_q8_0.gguf

SYSTEM """You are an expert in Ancient Latin sentiment analysis trained on 9,000 examples. You classify Latin texts into seven emotional categories:

Categories:
- EXTREMELY POSITIVE (+3): exsultatio, jubilum, beatitudo, summa felicitas
- VERY POSITIVE (+2): gaudium, laetitia, amor, gloria, victoria, laudare
- MODERATELY POSITIVE (+1): felix, laetus, bonus, pulcher, spes
- NEUTRAL (0): factual statements
- MODERATELY NEGATIVE (-1): malus, tristis, anxius, timor
- VERY NEGATIVE (-2): dolor magnus, timor vehemens, ira, furor
- EXTREMELY NEGATIVE (-3): desperatio, exitium, cruciatus, malum

Respond with ONLY the category name."""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_predict 20

TEMPLATE """{{ .System }}

Latin text: {{ .Prompt }}

Sentiment:"""
```

**Create the Ollama model:**
```bash
ollama create latin-sentiment-finetuned -f Modelfile.finetuned
```

**Time:** 1-2 minutes  
**Output:** Model ready to use in Ollama

#### Step 4: Test the Model

```bash
# Run the model
ollama run latin-sentiment-finetuned
```

**Test cases:**
```
>>> Victoria splendidissima! Dux gloriam aeternam meruit!
EXTREMELY POSITIVE

>>> Bellum crudele et longum populum afflixerat.
VERY NEGATIVE

>>> Consul in foro verba fecit.
NEUTRAL
```

---

## Using the Model

### Command Line

```bash
# Interactive mode
ollama run latin-sentiment-finetuned

# Single classification
echo "Victoria magna!" | ollama run latin-sentiment-finetuned
```

### Python API

```python
import requests
import json

def classify_latin(text):
    response = requests.post('http://localhost:11434/api/generate',
        json={
            "model": "latin-sentiment-finetuned",
            "prompt": text,
            "stream": False
        })
    return response.json()['response'].strip()

# Test
text = "Gaudium magnum populum cepit."
sentiment = classify_latin(text)
print(f"Sentiment: {sentiment}")
```

### REST API

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "latin-sentiment-finetuned",
  "prompt": "Victoria splendidissima!",
  "stream": false
}'
```

---

## Enhanced Accuracy with Intensity Rules

For 75% accuracy (same as research version), apply post-processing:

```python
import subprocess
import re

def classify_with_rules(latin_text):
    # Get model prediction
    result = subprocess.run(
        ['ollama', 'run', 'latin-sentiment-finetuned', latin_text],
        capture_output=True,
        text=True
    )
    prediction = result.stdout.strip()
    
    # Apply intensity rules (from intensity_rules.py)
    text_lower = latin_text.lower()
    
    # Extreme markers
    extreme_neg = ['crudel', 'saev', 'trucidat', 'perdi', 'desperatio']
    extreme_pos = ['splendidissim', 'magnificus', 'beatitudo', 'triumphus magnificus']
    
    has_extreme_neg = any(marker in text_lower for marker in extreme_neg)
    has_extreme_pos = any(marker in text_lower for marker in extreme_pos)
    exclamations = latin_text.count('!')
    
    # Adjust intensity
    if 'MODERATELY NEGATIVE' in prediction and has_extreme_neg:
        return 'VERY NEGATIVE'
    if 'MODERATELY POSITIVE' in prediction and has_extreme_pos and exclamations >= 2:
        return 'EXTREMELY POSITIVE'
    
    return prediction

# Test
text = "Victoria splendidissima! Dux gloriam aeternam meruit!"
print(classify_with_rules(text))  # EXTREMELY POSITIVE
```

---

## Troubleshooting

### "Model not found" error
```bash
# List available models
ollama list

# Recreate if needed
ollama create latin-sentiment-finetuned -f Modelfile.finetuned
```

### Out of memory
- Use smaller quantization: `q4_k_m` instead of `q8_0`
- Close other applications
- Requires 8GB+ RAM for 8-bit model

### Slow performance
- Use GPU version of Ollama (if you have NVIDIA GPU)
- Use smaller quantization (trades quality for speed)

### Wrong predictions
- Make sure you created the model from `Modelfile.finetuned` (not `Modelfile`)
- Apply intensity rules (see above) for 75% accuracy
- Model accuracy: ~70% in Ollama, 75% with rules

---

## File Sizes

| File | Size | Purpose |
|------|------|---------|
| Base Llama download | ~16GB | One-time download |
| Merged model (HF format) | ~16GB | Intermediate, can delete |
| GGUF q8_0 | ~8GB | Final Ollama model |
| GGUF q5_k_m | ~5GB | Smaller alternative |
| GGUF q4_k_m | ~4GB | Smallest option |

**Total disk needed:** ~40GB during conversion (can free up after)  
**Final disk usage:** ~8GB (just the GGUF file)

---

## Performance Comparison

| Method | Accuracy | Speed | Memory | Setup |
|--------|----------|-------|--------|-------|
| HuggingFace + GPU | 75% | Fast | 16GB GPU | 5 min |
| HuggingFace + CPU | 75% | Slow | 16GB RAM | 5 min |
| Ollama GGUF q8_0 | ~70% | Medium | 8GB RAM | 30 min |
| Ollama GGUF q4_0 | ~65% | Fast | 4GB RAM | 30 min |
| Ollama base + prompt | ~40% | Fast | 8GB RAM | 5 min |

**Recommendation:**
- **Research/Development:** Use HuggingFace (most accurate)
- **Local Demos:** Use Ollama GGUF q8_0 (good balance)
- **Quick Testing:** Use Ollama base model (easiest)

---

## Complete Script

Save this as `full_setup.sh` for automated setup:

```bash
#!/bin/bash
# Complete setup script for Latin sentiment model in Ollama

set -e  # Exit on error

echo "=========================================="
echo "Latin Sentiment Model - Ollama Setup"
echo "Team Trojan Parse"
echo "=========================================="

# 1. Install dependencies
echo "\\n[1/5] Installing dependencies..."
pip install torch transformers peft accelerate sentencepiece protobuf

# 2. Clone llama.cpp
echo "\\n[2/5] Cloning llama.cpp..."
if [ ! -d "llama.cpp" ]; then
    git clone https://github.com/ggerganov/llama.cpp
    cd llama.cpp
    pip install -r requirements.txt
    cd ..
fi

# 3. Download and merge model
echo "\\n[3/5] Downloading and merging model..."
python convert_latin_model.py

# 4. Convert to GGUF
echo "\\n[4/5] Converting to GGUF..."
cd llama.cpp
python convert-hf-to-gguf.py \\
    ../latin_sentiment_merged \\
    --outfile ../latin_sentiment_q8_0.gguf \\
    --outtype q8_0
cd ..

# 5. Create Ollama model
echo "\\n[5/5] Creating Ollama model..."
ollama create latin-sentiment-finetuned -f Modelfile.finetuned

echo "\\n=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo "\\nTest with: ollama run latin-sentiment-finetuned"
```

Run it:
```bash
chmod +x full_setup.sh
./full_setup.sh
```

---

## Support

- **Model:** https://huggingface.co/TronCodes/augustulus-latin-sentiment-lora
- **Ollama Docs:** https://ollama.ai/

---

**Created by Team Trojan Parse | University of Florida 2025**

