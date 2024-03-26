# Write wrapping function so that, if someone wants to use the GUI on a particular word, 
# it will call use dictionary function on CompleteCSVs, not post-results, then grab the
# full dataframe, strip it down to just text section, unindexed and without header, and 
# remove numbers from the text (clean a little)
# CSV Data should be single column without header

import re
import pandas as pd
import pickle
import grk_lemmatizer


def gui_wrapper(query_word, pkl_file, csv_file):

    #call query_data function to get the initial dataframe
    df = query_data(query_word, pkl_file, csv_file)

    #strip the dataframe to just text section
    text_df = df["Text Section"].values
    text_df = pd.DataFrame(text_df)

    #remove numbers from the text
    text_df = text_df.applymap(lambda x: re.sub(r'[\d\.\t\n]', '', str(x)))

    #write pandas dataframe to a text file and remove quotation marks
    text_df.to_csv(r'text_section.txt', header=None, index=None, mode='a', quoting=csv.QUOTE_NONE, quotechar='', escapechar=' ')


    return text_df


def query_data(query_word, input_file, data_table):

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



# gui_word = "φιλια"
# output_df = gui_wrapper(gui_word, "dictionary_grk.pkl", "0-50kgreekv1.csv")
# print(output_df)
