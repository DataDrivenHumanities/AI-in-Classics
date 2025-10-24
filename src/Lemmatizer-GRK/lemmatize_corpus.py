import os
from run_greek_lemmatizer import GreekLemmatizer

def main():
    lemmatizer = GreekLemmatizer()

    corpus_directory = "../../cleaned_xml"
    for f in os.listdir(corpus_directory):
        file_path = corpus_directory + "/" + f
        lemmatized_text = ""
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                content = file.read()
            except Exception as err:
                print(err)
            for word in content:
                res = lemmatizer.lemmatize(word)
                if len(res) > 0:
                    if res[0]["lemma"] != "nan":
                        lemmatized_text += res[0]["lemma"]
                    else:
                        lemmatized_text += word.lower()
                else:
                    lemmatized_text += word.lower()
            print(lemmatized_text)
            return

if __name__ == "__main__":
    main()