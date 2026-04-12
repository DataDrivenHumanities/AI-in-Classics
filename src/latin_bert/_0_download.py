import gdown

# Data
gdown.download_folder(
    id="1lB5jXr0eKPsehwo_269h4pb87ou4R0BO",
    output="./",
    quiet=False,
    remaining_ok=True,
)

# BASE MODELS
gdown.download_folder(
    id="1bS-0IG1K9Y4C6P50P0ZHVVVJcESujpA8",
    output="./models/",
    quiet=False,
    remaining_ok=True,
)


# Latest Trained Model
gdown.download_folder(
    id="1UXmSu22G-AaA1FL7tkOIHoMCVmshdJXa",
    output="./output/final_models/",
    quiet=False,
    remaining_ok=True,
)
