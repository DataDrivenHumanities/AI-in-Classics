from transformers import AutoModelForSequenceClassification

model = AutoModelForSequenceClassification.from_pretrained(
    "greekbert_v1/ancient-greek-text-classification-BERT",
    num_labels=8,
    id2label={
        0: "Anger",
        1: "Anticipation",
        2: "Disgust",
        3: "Fear",
        4: "Joy",
        5: "Sadness",
        6: "Surprise",
        7: "Trust"
    }
)
