from pprint import pprint

import numpy as np
import pandas as pd
from cltk.alphabet.text_normalization import cltk_normalize
from cltk.lemmatize.grc import GreekBackoffLemmatizer
from sklearn.feature_extraction.text import CountVectorizer

df = pd.read_csv(filepath_or_buffer="UpdatedCSV.csv")
pprint(df)

lemmatizer = GreekBackoffLemmatizer()
df_preprocess = pd.concat(
    objs=[
        df.loc[:, "Section ID"],
        df.loc[:, "Text Section"].agg(
            func=[
                cltk_normalize,
                lambda x: " ".join(list(zip(*lemmatizer.lemmatize(tokens=x)))[1]),
            ]
        ),
    ],
    axis=1,
)
df_preprocess.rename(
    dict(
        {df_preprocess.columns[1]: "Normalize", df_preprocess.columns[2]: "Lemmatize"}
    ),
    axis=1,
)
pprint(df_preprocess)

raise Exception

vectorizer = CountVectorizer(input="content")
X = vectorizer.fit_transform(raw_documents=df_preprocess.loc[:, "Lemmatize"])
doc_term_matrix = X.toarray()
pprint(doc_term_matrix.shape)
pprint(doc_term_matrix)
np.save(file="UpdatedDocTermMatrix.npy", arr=doc_term_matrix)
