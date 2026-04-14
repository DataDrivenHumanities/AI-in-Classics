from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from bert_utils.tokenizer import LatinHFTokenizer
from datetime import datetime
from pathlib import Path
import torch
import numpy as np
from sklearn.metrics import f1_score, accuracy_score

# ── Model / tokenizer toggle ──────────────────────────────────────────────────
if False:
    MODEL_PATH = "bert-base-multilingual-cased"
    TOKENIZER_PATH = "bert-base-multilingual-cased"
    TOKENIZER = AutoTokenizer.from_pretrained(TOKENIZER_PATH)
else:
    MODEL_PATH = "models/bert_models/latin_bert"
    TOKENIZER_PATH = "models/bert_models/subword_tokenizer_latin/latin.subword.encoder"
    TOKENIZER = LatinHFTokenizer(TOKENIZER_PATH)

# ── Blackwell-specific flags ──────────────────────────────────────────────────
torch.backends.cuda.matmul.allow_tf32 = True  # free ~10 % throughput on matmuls
torch.backends.cudnn.allow_tf32 = True
torch.set_float32_matmul_precision("high")  # required for torch.compile + TF32

# ── Dataset ───────────────────────────────────────────────────────────────────
dataset = load_dataset("json", data_files="data/bert_data/train4.jsonl")
split_ds = dataset["train"].train_test_split(test_size=0.1, seed=42)


def tokenize(batch):
    return TOKENIZER(
        batch["sentence"],
        truncation=True,
        padding="max_length",
        max_length=128,
    )


# num_proc speeds up tokenisation on CPU while GPU trains
train_set = split_ds["train"].map(tokenize, batched=True, num_proc=4)
val_set = split_ds["test"].map(tokenize, batched=True, num_proc=4)

train_set.set_format("torch", columns=["input_ids", "attention_mask", "label"])
val_set.set_format("torch", columns=["input_ids", "attention_mask", "label"])


# ── Metrics ───────────────────────────────────────────────────────────────────
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1_macro": f1_score(labels, preds, average="macro"),
    }


# ── Effective batch size = 64  (8 devices × 8 grad-accum steps) ──────────────
# Larger effective batch → smoother gradients, lets you raise LR safely.
PER_DEVICE_BATCH = 32  # 5080 has 16 GB — BERT-base fits at 32 easily
GRAD_ACCUM_STEPS = 2  # effective batch = 64; raise to 4 if OOM
EPOCHS = 50
WARMUP_RATIO = 0.06  # ~6 % of steps for LR warm-up

RUN_NAME = f"{Path(MODEL_PATH).name}_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}"

training_args = TrainingArguments(
    output_dir=f"./output/intermediate/{RUN_NAME}",
    run_name=RUN_NAME,
    # ── Batch / accumulation ─────────────────────────────────────────────────
    per_device_train_batch_size=PER_DEVICE_BATCH,
    per_device_eval_batch_size=PER_DEVICE_BATCH * 2,  # eval needs no backward pass
    gradient_accumulation_steps=GRAD_ACCUM_STEPS,
    # ── Precision  (BF16 is first-class on Blackwell, unlike FP16) ───────────
    bf16=True,
    bf16_full_eval=True,
    # ── Optimizer  (fused AdamW avoids Python overhead per-param) ────────────
    optim="adamw_torch_fused",
    learning_rate=3e-5,
    weight_decay=0.01,
    warmup_ratio=WARMUP_RATIO,
    lr_scheduler_type="cosine",  # cosine decay is gentler than linear near end
    # ── Epochs / eval / checkpoint ───────────────────────────────────────────
    num_train_epochs=EPOCHS,
    eval_strategy="epoch",
    logging_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1_macro",
    greater_is_better=True,
    save_total_limit=3,  # keep only the 3 best checkpoints
    # ── DataLoader workers (feed GPU without stalling) ───────────────────────
    dataloader_num_workers=4,
    dataloader_pin_memory=True,  # zero-copy transfer to GPU
    # ── torch.compile  (Blackwell + PyTorch ≥ 2.x = big win) ────────────────
    torch_compile=True,
    torch_compile_backend="inductor",
    # ── Gradient checkpointing  (trade recompute for VRAM headroom) ──────────
    # Uncomment if you hit OOM or want to push batch size higher:
    # gradient_checkpointing=True,
    # ── Reproducibility ──────────────────────────────────────────────────────
    seed=42,
    data_seed=42,
)

# ── Model ─────────────────────────────────────────────────────────────────────
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=3)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_set,
    eval_dataset=val_set,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=10)],
)

trainer.train()
trainer.save_model(f"./output/final_models/{RUN_NAME}")
