#Creating the functions
import pandas as pd

LTN_WORDS_CSV = "lemmas.csv"

#load in the dataframes for functions
lemmaDF = pd.read_csv(LTN_WORDS_CSV, sep = "{")
del lemmaDF['Unnamed: 0']
#parsesDF = pd.read_csv("Dictionary_Dataframes/parses.csv", sep = "{")
#del parsesDF["Unnamed: 0"]

#outputs list of matching IDs or an empty list
def get_id(word):
    #search the lemmaDF for the word
    output = []
    #this is the dataframe of all rows with the word
    df = lemmaDF.loc[lemmaDF["bare_text"] == word]
        #iterrows works, but the others dont. ok whatever
    for index, row in df.iterrows():
        if(row["id"] not in output):
            output.append(row["id"])
    return(output)
