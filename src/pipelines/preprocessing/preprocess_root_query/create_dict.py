from enum import Enum
import csv
import sys
import pickle
import argparse
import os


import grk_lemmatizer
import ltn_lemmatizer


GRK_CSV = "0-50kgreekv1.csv"
LTN_CSV = ""


class Language(Enum):
    GRK = 1
    LTN = 2


# Global file_obj, so it can be closed when done using
file_obj = None


def exit():
    try:
        file_obj.close()
    except Exception:
        pass

    print("Exiting...")

    sys.exit()
    

def load_csv(lang: Language) -> csv.reader:
    file_name = ""

    if lang == Language.GRK:
        file_name = GRK_CSV
    elif lang == Language.LTN:
        file_name = LTN_CSV

    # Open CSV file
    try:
        file_obj = open(f"{file_name}", 'r', encoding='utf-8')
        reader_obj = csv.reader(file_obj)
        print("File ", file_name, " opened successfully.")
    except IOError:
        print("Failed to open file: ", file_name)
        exit()

    return reader_obj


# Old function, tokenizes all possible phrase combinations
#def tokenize_aspect(aspect: str):
    # Tokenize the aspect into all space-delimited combinations
    # Unsure if this is necessary; if not, .split() function is all that is needed
    #l = aspect.split()
    #sep = [(" ", ";") for i in range(len(l)-1)]
    #t = "{}".join(l)
    #res = [t.format(*s).split(";") for s in product(*sep)]

    # Flatten the list of lists that is generated
    #aspect_tokens = [x for xs in res for x in xs]
    
    #return aspect_tokens


def init_dict(lang: Language, force = None, limit = None):

    # Make sure we're not overwriting an existing dictionary
    # if exists -> error

    suffix = 'grk' if lang == Language.GRK else 'ltn'
    dict_filename = f"dictionary_{suffix}.pkl"
    if os.path.isfile(dict_filename):
        if not force:
            print("Pickled dictionary file already exists. Delete it and rerun or run with --force.")
            exit()

    csv_reader = load_csv(lang)

    # CSV Format:
    # ['', 'Unnamed: 0.1', 'Unnamed: 0', 'Section ID', 
    # 'Text Section', 'Title', 'Author', 'Translated Text',
    # 'TreePath', 'aspect', 'confidence', 'sentiment'] 
    
    # Initialize dictionary
    dictionary = dict()
    
    # Skip first row of column headers
    next(csv_reader)


    i = 0 # Index rows starting at 0 for the first data entry
    for row in csv_reader:

        # if i >= 100: break

        if limit:
            if i >= limit: break

        print(i)

        aspect = row[9]
        words = aspect.split()
        ids = []
        for word in words:
            if lang == Language.GRK:
                ids.extend(grk_lemmatizer.get_id(word))
            else:
                ids.extend(ltn_lemmatizer.get_id(word))

        if ids: print(ids)

        for id in ids:
            if id not in dictionary:
                dictionary[id] = [i]
            else:
                dictionary[id].append(i)

        i += 1


    print(dictionary)

    # 'x' command option returns an error if the file already exists
    # Rationale: Prevent from accidentally overwriting

    if not force:
        try:
            with open(f"dictionary_{suffix}.pkl", "xb") as f:
                pickle.dump(dictionary, f)
        except FileExistsError:
            print("Pickled dictionary file already exists. Delete it and rerun or run with --force.")
            exit()
    else:
        with open(f"dictionary_{suffix}.pkl", "wb") as f:
            pickle.dump(dictionary, f)

    
    exit()




def main():
    parser = argparse.ArgumentParser(
        description="Script that creates and serializes a dictionary for querying word IDs."
    )
    parser.add_argument("-g", action='store_true')
    parser.add_argument("-l", action='store_true')
    parser.add_argument("--force", required=False, action='store_true')
    parser.add_argument("--limit", required=False, type=int)
    # Consider adding more args for specifying I/O file names

    args = parser.parse_args()

    lang = None
    force = args.force
    limit = None
    if args.limit: limit = args.limit
    

    if args.g and not args.l:
        lang = Language.GRK
    elif args.l and not args.g:
        lang = Language.LTN
    else:
        choice = None
        while not choice:
            choice = input("Choose:\n\t1. Greek\n\t2. Latin\n")
            
            if choice == '1': 
                lang = Language.GRK
            elif choice == '2': 
                lang = Language.LTN
            else: 
                choice = None

    init_dict(lang, force, limit)

    exit()

if __name__ == "__main__":
    main()


