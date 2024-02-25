import grk_lemmatizer
import pickle

phrase = str(input("Enter phrase to lookup: "))

words = phrase.split()

# τοξαρις η φιλια

# φιλια found row 0
# φιλιος found in row 125
# φιλιας found in row 219

ids = []

for word in words:
    ids.extend(grk_lemmatizer.get_id(word))

# ids = grk_lemmatizer.get_id(word)

print("Associated ids: ", ids)

file = open("dictionary_grk.pkl",'rb')

dictionary = pickle.load(file)

for id in ids:
    if id in dictionary:
        print("Id [", id, "] found in rows: ", dictionary[id])


# Enter phrase to lookup: φιλια
# Associated ids:  [34792, 34795]
# Id [ 34792 ] found in rows:  [1, 220, 477]
# Id [ 34795 ] found in rows:  [1, 126, 220, 477]
