import os
from transformers import AutoTokenizer, AutoModelForMaskedLM, DataCollatorForLanguageModeling, TrainingArguments, Trainer
from datasets import Dataset, DatasetDict

def split_dataset(input_path):
    train_data = []
    test_data = []
    file_count = 0
    # read files from parent path
    for filename in os.listdir(input_path):
        file_path = os.path.join(input_path, filename)
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
    # split text corpus into train and test sets
    train_data, test_data = split_dataset("../../data/greek/lemmatized_text")
    print(train_data)
    dataset = DatasetDict({
        "train": Dataset.from_list(train_data),
        "test": Dataset.from_list(test_data)
    })
    # establish base tokenizer
    tokenizer = AutoTokenizer.from_pretrained("luvnpce83/ancient-greek-emotion-bert")

    def pre_process_tokens(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=128,
        )

    # pre tokenize corpus
    tokenized = dataset.map(pre_process_tokens, batched=True, remove_columns=["text"])

    model = AutoModelForMaskedLM.from_pretrained("luvnpce83/ancient-greek-emotion-bert")

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=0.5
    )

    training_args = TrainingArguments(
        output_dir="greekbert_v1/ancient-greek-text-classification-BERT",
        learning_rate=5e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=3,
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
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    # --- 7. Continue training ---
    trainer.train()

    # --- 8. Save adapted model ---
    trainer.save_model("./ancient-greek-text-classification-BERT-2")

if __name__ == "__main__":
    main()