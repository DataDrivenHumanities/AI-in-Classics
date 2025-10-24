import glob
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, normalizers

tokenizer = Tokenizer(models.BPE())
tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
trainer = trainers.BpeTrainer(vocab_size=30000, special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"])
tokenizer.train(["lemmatized_corpus.txt"], trainer)
tokenizer.save("greek_lemma_tokenizer.json")
