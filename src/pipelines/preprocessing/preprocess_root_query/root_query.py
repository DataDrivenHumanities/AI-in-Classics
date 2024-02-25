import pickle
import pandas as pd
import grk_lemmatizer

#parameters - pickle file, query word, data table 
def query_data(input_file, query_word, data_table):

    #place contents of pickle file into dictionary container 
    with open(input_file, 'rb') as file:
        dictionary = pickle.load(file)

    ids_from_word = grk_lemmatizer.get_id(query_word)  #transform word to list of ids with lemmatizer

    data_table = pd.read_csv(data_table, delimiter=',', header = 0)  #load csv file into dataframe

    final_table = pd.DataFrame()   #create empty dataframe

    #go through each id and get row
    for id_from_word in ids_from_word:
        if id_from_word in dictionary:
            #print(f"This is the id: {id_from_word}")
                                
            #get row index and then get the entire row based on the index
            row_index = dictionary[id_from_word]
            dataframe_row = data_table.iloc[row_index]
                
            #print(dataframe_row)
                
            #append row to final table
            final_table = pd.concat([final_table, pd.DataFrame(dataframe_row)], ignore_index=True)

        else: 
            print(f"{query_word} doesn't exist.")
            return -1

    return final_table


result = query_data("src/pipelines/preprocessing/preprocess_root_query/needed_files/dictionary_grk.pkl", "φιλια", "src/pipelines/preprocessing/preprocess_root_query/needed_files/0-50kgreekv1.csv")
print(result)