import pandas as pd

GRK_WORDS_CSV = (
    "src/pipelines/preprocessing/preprocess_root_query/needed_files/greek_words.csv"
)

# load in the dataframes for functions
lemmaDF = pd.read_csv(GRK_WORDS_CSV, sep="\t")
del lemmaDF["Unnamed: 0"]


# outputs list of matching IDs or an empty list
def get_id(word):
    # search the lemmaDF for the word
    word = word.lower()
    output = []
    # this is the dataframe of all rows with the word
    df = lemmaDF.loc[lemmaDF["bare_text"] == word]
    # iterrows works, but the others dont. ok whatever
    for index, row in df.iterrows():
        if row["id"] not in output:
            output.append(row["id"])
    return output
