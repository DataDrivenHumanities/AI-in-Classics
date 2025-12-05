import os
import evaluate
import numpy as np
from transformers import AutoTokenizer, TrainingArguments, \
    Trainer, AutoModelForSequenceClassification, DataCollatorWithPadding
from datasets import Dataset, DatasetDict
import torch
import torch.nn.functional as F
from tqdm import tqdm
import pandas as pd

def split_dataset(data: list):
    train_data = []
    test_data = []
    # read files from parent path
    for i, row in enumerate(data):
        if (i % 2) == 0:  # even
            train_data.append(row)

        else:
            test_data.append(row)
    return train_data, test_data


def main():
    output_dir = "greekbert_v2/ancient-greek-text-classification-BERT-2"

    id2label = {
        "0": "Anger",
        "1": "Anticipation",
        "2": "Disgust",
        "3": "Fear",
        "4": "Joy",
        "5": "Sadness",
        "6": "Surprise",
        "7": "Trust"
    }
    label2id = {
        "Anger": "0",
        "Anticipation": "1",
        "Disgust": "2",
        "Fear": "3",
        "Joy": "4",
        "Sadness": "5",
        "Surprise": "6",
        "Trust": "7"
    }

    df = pd.read_csv("../../data/greek/lemmatized_csv/lemmatized_sentences.csv")
    # establish base tokenizer
    pre_trained_model = "luvnpce83/ancient-greek-emotion-bert"
    tokenizer = AutoTokenizer.from_pretrained(pre_trained_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        pre_trained_model,
        num_labels=8,
        id2label=id2label,
        label2id=label2id
    )

    pseudo_labels = []

    for item in tqdm(df.itertuples()):
        sentence = item.sentence
        inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1)
            conf, label_id = torch.max(probs, dim=-1)
            if conf.item() > 0.90:
                pseudo_labels.append({"text": sentence, "label": int(label_id), "score": float(conf)})

    train_data, test_data = split_dataset(pseudo_labels)
    print(train_data[0])
    print(test_data[0])
    dataset = DatasetDict({
        "train": Dataset.from_list(train_data),
        "test": Dataset.from_list(test_data)
    })

    def process_tokens_function(examples):
        tokens = tokenizer(
            examples["text"],
            max_length=512,
            truncation=True,
        )
        tokens["label"] = examples["label"]
        return tokens

    # pre tokenize corpus
    tokenized = dataset.map(process_tokens_function, batched=True)

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    accuracy = evaluate.load("accuracy")

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        probs = np.exp(predictions) / np.exp(predictions).sum(-1, keepdims=True)  # softmax
        predictions = np.argmax(probs, axis=1)
        confidences = probs.max(axis=1)
        return {
            "accuracy": accuracy.compute(predictions=predictions, references=labels)["accuracy"],
            "avg_confidence": float(np.mean(confidences)),
        }

    training_args = TrainingArguments(
        output_dir=output_dir,
        learning_rate=5e-5,
        per_device_train_batch_size=64,
        per_device_eval_batch_size=64,
        num_train_epochs=12,
        weight_decay=0.01,
        save_total_limit=2,
        push_to_hub=False,
        logging_dir='./logs',
        logging_steps=100,
    )

    # --- 6. Trainer ---
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    # --- 7. Continue training ---
    trainer.train()

    # --- 8. Save adapted model ---
    trainer.save_model(output_dir)

    accuracy = evaluate.load("accuracy")

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        probs = np.exp(predictions) / np.exp(predictions).sum(-1, keepdims=True)  # softmax
        predictions = np.argmax(probs, axis=1)
        confidences = probs.max(axis=1)
        return {
            "accuracy": accuracy.compute(predictions=predictions, references=labels)["accuracy"],
            "avg_confidence": float(np.mean(confidences)),
        }

    training_args = TrainingArguments(
        output_dir=output_dir,
        learning_rate=5e-5,
        per_device_train_batch_size=64,
        per_device_eval_batch_size=64,
        num_train_epochs=12,
        weight_decay=0.01,
        save_total_limit=2,
        push_to_hub=False,
        logging_dir='./logs',
        logging_steps=100,
        load_best_model_at_end=True
    )

    # --- 6. Trainer ---
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    # --- 7. Continue training ---
    trainer.train()

    # --- 8. Save adapted model ---
    trainer.save_model(output_dir)

if __name__ == "__main__":
    main()