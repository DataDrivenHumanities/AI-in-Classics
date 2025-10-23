import os

from autotrain.params import LLMTrainingParams
from autotrain.project import AutoTrainProject


params = LLMTrainingParams(
    model="rtwins/ancient-greek-bert-v1",
    data_path="",
    chat_template="tokenizer",
    text_column="messages",
    train_split="train",
    trainer="sft",
    epochs=1,
    batch_size=64,
    lr=1e-5,
    peft=True,
    quantization="int4",
    target_modules="all-linear",
    padding="right",
    optimizer="paged_adamw_8bit",
    scheduler="cosine",
    gradient_accumulation=8,
    mixed_precision="bf16",
    merge_adapter=True,
    project_name="ancient-greek-bert-rtwins",
    log="tensorboard",
    push_to_hub=True,
    username=os.environ.get("HF_USERNAME"),
    token=os.environ.get("HF_TOKEN"),
)


backend = "local"
project = AutoTrainProject(params=params, backend=backend, process=True)
project.create()