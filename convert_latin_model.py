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

# base_model = AutoModelForCausalLM.from_pretrained(
#     "meta-llama/Llama-3.1-8B-Instruct",
#     torch_dtype=torch.float16,
#     device_map="auto",
#     trust_remote_code=True
# )

# base_model = AutoModelForCausalLM.from_pretrained(
#     "meta-llama/Llama-3.1-8B-Instruct",
#     torch_dtype=torch.float32,
#     device_map=None,
# )

base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B-Instruct",
    torch_dtype=torch.bfloat16,   # or torch.float16
    device_map=None,
)

# print("✓ Base model loaded")
print("base model loaded")

# Step 2: Load our fine-tuned adapter from HuggingFace
print("\\n[2/4] Loading Team Trojan Parse adapter...")
print("From: TronCodes/augustulus-latin-sentiment-lora")

model = PeftModel.from_pretrained(
    base_model,
    "TronCodes/augustulus-latin-sentiment-lora"
)
# print("✓ Adapter loaded")
print("Adapter loaded")


# Step 3: Merge adapter into base model
print("\\n[3/4] Merging adapter into base model...")
print("(This creates a single model with our training)")

merged_model = model.merge_and_unload()
# print("✓ Merged successfully")
print("Merged successfully")


# Step 4: Save merged model
print("\\n[4/4] Saving merged model...")
output_dir = "./latin_sentiment_merged"

merged_model.save_pretrained(output_dir, safe_serialization=True)

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
tokenizer.save_pretrained(output_dir)

print(f"Saved to: {output_dir}")
# print(f"✓ Saved to: {output_dir}")

print("\\n" + "="*70)
print("Merge complete! Next: Convert to GGUF")
print("="*70)