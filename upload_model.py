from huggingface_hub import HfApi

api = HfApi()
api.create_repo(repo_id="rtwins/greekbert_for_text_classification", repo_type="model")
api.upload_folder(
    folder_path="src/SentimentAnalysisGreek/greekbert_v2/ancient-greek-text-classification-BERT-2",
    repo_id="rtwins/greekbert_for_text_classification",
    repo_type="model",

)