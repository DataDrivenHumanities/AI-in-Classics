from datasets import load_dataset
from transformers import AutoTokenizer
from transformers import AutoModelForSequenceClassification
from transformers import TrainingArguments, Trainer
from cltk.tokenizers.lat.lat import LatinWordTokenizer as WordTokenizer
from cltk.tokenizers.lat.lat import LatinPunktSentenceTokenizer as SentenceTokenizer
from tensor2tensor.data_generators import text_encoder
import torch


class LatinTokenizer:
    def __init__(self, encoder):
        self.vocab = {}
        self.reverseVocab = {}
        self.encoder = text_encoder.SubwordTextEncoder(encoder)

        self.vocab["[PAD]"] = 0
        self.vocab["[UNK]"] = 1
        self.vocab["[CLS]"] = 2
        self.vocab["[SEP]"] = 3
        self.vocab["[MASK]"] = 4

        for key in self.encoder._subtoken_string_to_id:
            self.vocab[key] = self.encoder._subtoken_string_to_id[key] + 5
            self.reverseVocab[self.encoder._subtoken_string_to_id[key] + 5] = key

    def convert_tokens_to_ids(self, tokens):
        wp_tokens = []
        for token in tokens:
            if token == "[PAD]":
                wp_tokens.append(0)
            elif token == "[UNK]":
                wp_tokens.append(1)
            elif token == "[CLS]":
                wp_tokens.append(2)
            elif token == "[SEP]":
                wp_tokens.append(3)
            elif token == "[MASK]":
                wp_tokens.append(4)

            else:
                wp_tokens.append(self.vocab[token])

        return wp_tokens

    def tokenize(self, text):
        tokens = text.split(" ")
        wp_tokens = []
        for token in tokens:

            if token in {"[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"}:
                wp_tokens.append(token)
            else:

                wp_toks = self.encoder.encode(token)

                for wp in wp_toks:
                    wp_tokens.append(self.reverseVocab[wp + 5])

        return wp_tokens

    def convert_to_toks(self, sents):

        sent_tokenizer = SentenceTokenizer()
        word_tokenizer = WordTokenizer()

        all_sents = []

        for data in sents:
            text = data.lower()

            sents = sent_tokenizer.tokenize(text)
            for sent in sents:
                tokens = word_tokenizer.tokenize(sent)
                filt_toks = []
                filt_toks.append("[CLS]")
                for tok in tokens:
                    if tok != "":
                        filt_toks.append(tok)
                filt_toks.append("[SEP]")

                all_sents.append(filt_toks)

        return all_sents


class LatinHFTokenizer:
    def __init__(self, latin_tokenizer):
        self.latin_tokenizer = LatinTokenizer(latin_tokenizer)

    def __call__(
        self,
        texts,
        truncation=True,
        padding="max_length",
        max_length=128,
        return_tensors="pt",
    ):
        """
        Args:
            texts: str or list of str
            truncation: truncate sequences longer than max_length
            padding: "max_length" to pad to max_length
            max_length: int, maximum sequence length
            return_tensors: "pt" for PyTorch, "np" for NumPy, None for plain Python lists
        """
        if isinstance(texts, str):
            texts = [texts]

        all_ids = []
        all_masks = []

        for text in texts:
            # convert to tokens
            toks = self.latin_tokenizer.convert_to_toks([text])[0]

            # wordpiece tokenize
            wp_tokens = []
            for tok in toks:
                wp_tokens.extend(self.latin_tokenizer.tokenize(tok))

            ids = self.latin_tokenizer.convert_tokens_to_ids(wp_tokens)

            # truncate
            ids = ids[:max_length]

            mask = [1] * len(ids)

            # pad
            pad_len = max_length - len(ids)
            ids += [0] * pad_len
            mask += [0] * pad_len

            all_ids.append(ids)
            all_masks.append(mask)

        # Convert to desired tensor type
        if return_tensors == "pt":
            import torch

            all_ids = torch.tensor(all_ids)
            all_masks = torch.tensor(all_masks)
        elif return_tensors == "np":
            import numpy as np

            all_ids = np.array(all_ids)
            all_masks = np.array(all_masks)
        # else leave as Python lists

        return {
            "input_ids": all_ids,
            "attention_mask": all_masks,
        }
