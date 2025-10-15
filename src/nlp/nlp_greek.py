from pprint import pprint

import spacy

passage = """
Χρὴ γινώσκειν ὅτι πάσης τῆς γῆς ὁ περίμετρος. στάδιά ἐστι δισχίλια καὶ μυριάδες εἴκοσι πέντε· μῆκος δὲ τῆς ἡμετέρας οἰκουμένης ἀπὸ στόματος Γάγγου ἕως Γαδείρων στάδια ὀκτακισμύρια τρισχίλια ὀκ τακόσια·
τὸ δὲ πλάτος ἀπὸ τῆς Αἰθιοπικῆς θαλάσσης ἕως τοῦ Τανάϊδος ποταμοῦ στάδια τρισμύρια πεντακισχίλια τὸ δὲ μεταξὺ Εὐφράτου καὶ Τίγριδος ποταμοῦ, ὃ καλεῖται Μεσοποτάμιον, διάστημα ἔχει σταδίων τρισχιλίων, Ταύτην τὴν ἀναμέτρησιν πεποίηκεν Ἐρατοσθένης
ὁ τῶν ἀρχαίων μαθητικώτατος.
"""

nlp = spacy.load("el_core_news_lg")
doc = nlp(passage)
pprint(doc.text)

for token in doc:
    print(f"Token: {token}")
    print(
        token.text,
        token.lemma_,
        token.pos_,
        token.tag_,
        token.dep_,
        token.shape_,
        token.is_alpha,
        token.is_stop,
    )
