import os
from transformers import AutoTokenizer, AutoModelForMaskedLM, DataCollatorForLanguageModeling, TrainingArguments, \
    Trainer, AutoModelForSequenceClassification, DataCollatorWithPadding
from datasets import Dataset, DatasetDict

def split_dataset(input_path):
    train_data = []
    test_data = []
    file_count = 0
    # read files from parent path
    for filename in os.listdir(input_path):
        file_path = os.path.join(input_path, filename)
        if not str(filename).endswith(".txt"):
            continue
        content = ""
        print(f"Reading {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()  # reads text into string
        if (file_count % 2) == 0:  # even
            train_data.append({
                "text": content
            })
        else:
            test_data.append({
                "text": content
            })
        file_count += 1
    return train_data, test_data

def main():
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
    # split text corpus into train and test sets
    train_data, test_data = split_dataset("../../data/greek/lemmatized_text")
    dataset = DatasetDict({
        "train": Dataset.from_list(train_data),
        "test": Dataset.from_list(test_data)
    })
    # establish base tokenizer
    tokenizer = AutoTokenizer.from_pretrained("luvnpce83/ancient-greek-emotion-bert")

    def pre_process_tokens(examples):
        return tokenizer(
            examples["text"],
            max_length=512,
            truncation=True,
        )

    # pre tokenize corpus
    tokenized = dataset.map(pre_process_tokens, batched=True, remove_columns=["text"])

    model = AutoModelForSequenceClassification.from_pretrained(
        "luvnpce83/ancient-greek-emotion-bert",
        num_labels=8,
        id2label=id2label,
        label2id=label2id
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    training_args = TrainingArguments(
        output_dir="greekbert_v1/ancient-greek-text-classification-BERT-2",
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
    )

    # --- 7. Continue training ---
    trainer.train()

    # --- 8. Save adapted model ---
    trainer.save_model("greekbert_v1/ancient-greek-text-classification-BERT-2")

if __name__ == "__main__":
    main()