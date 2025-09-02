import dill
import io
import multiprocessing as mp
import numpy as np
import pandas as pd
import os
import shutil
import time
import tqdm
import sys

# Add project root to path to import utils
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import our utilities if available
try:
    from src.utils.logging_utils import setup_logger
    from src.utils.cache_utils import cache
    from src.utils.lemmatizer_utils import wrap_lemmatizer
    # Set up logger
    logger = setup_logger('app_functions')
except ImportError:
    # Fallback logging if modules aren't available
    import logging
    logger = logging.getLogger('app_functions')
    logging.basicConfig(level=logging.INFO)
    
    # Create a dummy cache if import fails
    class DummyCache:
        def has(self, key): return False
        def get(self, key, default=None): return default
        def set(self, key, value): pass
    cache = DummyCache()
    
        # Not needed anymore as we're implementing caching directly

# CLTK
from cltk.data.fetch import FetchCorpus
from cltk.lemmatize.grc import GreekBackoffLemmatizer
from cltk.alphabet.text_normalization import cltk_normalize

grc_corpus = FetchCorpus(language='grc')
grc_corpus.import_corpus(corpus_name='grc_models_cltk')

# Create an inline caching wrapper for the lemmatizer
class CachedLemmatizer:
    """A wrapper for the CLTK lemmatizer with caching for performance improvements"""
    
    def __init__(self, lemmatizer):
        self.lemmatizer = lemmatizer
        self.cache = {}
        self.stats = {"hits": 0, "misses": 0}
        logger.info("Initialized cached lemmatizer wrapper")
    
    def lemmatize(self, tokens):
        """Lemmatize a list of tokens with caching"""
        results = []
        
        for token in tokens:
            # Create a cache key - just use the token itself
            cache_key = token.lower().strip()
            
            # Check cache
            if cache_key in self.cache:
                # Cache hit
                lemma = self.cache[cache_key]
                results.append((token, lemma))
                self.stats["hits"] += 1
            else:
                # Cache miss - call the real lemmatizer
                lemma_result = self.lemmatizer.lemmatize([token])
                if lemma_result:
                    original, lemma = lemma_result[0]
                    # Store in cache
                    self.cache[cache_key] = lemma
                    results.append((token, lemma))
                else:
                    # Fallback if lemmatization fails
                    results.append((token, token))
                self.stats["misses"] += 1
        
        # Log stats periodically
        total = self.stats["hits"] + self.stats["misses"]
        if total % 100 == 0 and total > 0:
            hit_rate = (self.stats["hits"] / total) * 100 if total > 0 else 0
            logger.debug(f"Lemmatizer cache: {self.stats['hits']} hits, {self.stats['misses']} misses, {hit_rate:.1f}% hit rate")
            
        return results

# Create the base lemmatizer
base_lemmatizer = GreekBackoffLemmatizer()

# Wrap with caching
lemmatizer = CachedLemmatizer(base_lemmatizer)
logger.info(f"Greek lemmatizer initialized with caching")

# MACHINE LEARNING
from sklearn.feature_extraction.text import CountVectorizer

# APP DEVELOPMENT
import streamlit as st
from globals import globals

# OTHER GLOBAL VARIABLES
PREPROCESS_CHECKPOINT = False
DTM_CHECKPOINT = False
HISTORY = list()

# Get DEBUG from globals instead of hardcoding
DEBUG = globals.get('DEBUG', False)

# Set up caching flag
USE_CACHE = True  # Can be toggled via settings in the future

# CALLBACKS
#region
def dtm_cb():
    DOC_TERM_MATRIX = globals['DOC_TERM_MATRIX']
    VOCABULARY = globals['VOCABULARY']
    sorted_vocab = sorted(list(VOCABULARY.keys()))
    
    # display data
    if DOC_TERM_MATRIX is None:
        st.warning(body='WARNING (DTM CALLBACK): Cannot perform analysis on empty data.')
        return
    
    st.caption(body='Figure 1. Document-term matrix.')
    st.dataframe(data=DOC_TERM_MATRIX)
    st.caption(body='Figure 2. Sample subset of sorted and lemmatized vocabulary.')
    st.write(sorted_vocab[100:110])
    
    with st.expander(label='Download', expanded=False):
        # download document-term matrix
        with io.BytesIO() as buffer:
            np.save(file=buffer, arr=DOC_TERM_MATRIX)
            st.download_button(
                label='Download DTM',
                data=buffer,
                file_name='doc-term-matrix.npy',
                mime='text/npy',
                help='Download document-term matrix as Numpy file.'
            )
            
        # download vocabulary
        if st.button(
            label='Download Vocabulary',
            help='Save list of all unique stem words of corpus as text file.'
        ):
            if DEBUG:
                st.write(sorted_vocab[:10])
                print(sorted_vocab[:10])
            
            with open(file='./vocabulary.txt', mode='a', encoding='utf-8') as f:
                prog = st.progress(value=0.0)
                for index, vocab in tqdm.tqdm(enumerate(sorted_vocab)):
                    prog.progress(value=float(index + 1) / len(sorted_vocab))
                    f.write(f'{vocab}\n')

def dir_path_cb():
    global HISTORY
    global PREPROCESS_CHECKPOINT
    FULL_TEXTS_PATH = globals['FULL_TEXTS_PATH']
    PREPROCESSED_TEXTS_PATH = globals['PREPROCESSED_TEXTS_PATH']
    dir_path = os.path.abspath(path=globals['dir_path_input'])
        
    # debugging
    if DEBUG:
        st.write(FULL_TEXTS_PATH)
        st.write(dir_path)
        st.write(HISTORY)
    
    # check for valid path
    if os.path.exists(path=dir_path):
        # check existence of only .txt files
        if not np.all(a=list([os.path.splitext(p=path)[1] == '.txt' for path in os.listdir(path=dir_path)])):
            st.error(body='ERROR (DIRECTORY PATH CALLBACK): Directory path contains nested directories.')
            return

        # check for different data source than last load
        source_changed = False
        if len(HISTORY) == 0 or (HISTORY[0] != dir_path if len(HISTORY) == 1 else HISTORY[-2] != dir_path):
            source_changed = True
            HISTORY.append(dir_path)
            shutil.rmtree(path=PREPROCESSED_TEXTS_PATH, ignore_errors=True)
            os.makedirs(name=PREPROCESSED_TEXTS_PATH, exist_ok=True)
            
        if(len(os.listdir(path=dir_path)) == 0):
            st.warning(body='WARNING (DIRECTORY PATH CALLBACK): No files detected in directory path:')

        globals['FULL_TEXTS_PATH'] = dir_path
        globals['UPLOADED_DATA_NAME'] = dir_path
        PREPROCESS_CHECKPOINT = True
        st.success(body=f'SUCCESS (DIRECTORY PATH CALLBACK): Confirmed directory path. {"Path has changed since last load." if source_changed else "Same path as last load."}')
    else:
        st.error(body=f'ERROR (DIRECTORY PATH CALLBACK): The path does not exist.')

def csv_upload_cb():
    global PREPROCESS_CHECKPOINT
    FULL_TEXTS_PATH = globals['FULL_TEXTS_PATH'] = './full_texts/'
    PREPROCESSED_TEXTS_PATH = globals['PREPROCESSED_TEXTS_PATH']
    csv_file = globals['csv_file']

    # check for different data source than last load
    source_changed = False
    if globals['UPLOADED_DATA_NAME'] != csv_file.name:
        source_changed = True
        
        # resetting temporary directories
        shutil.rmtree(path=FULL_TEXTS_PATH, ignore_errors=True)
        shutil.rmtree(path=PREPROCESSED_TEXTS_PATH, ignore_errors=True)
        os.makedirs(name=FULL_TEXTS_PATH, exist_ok=True)
        os.makedirs(name=PREPROCESSED_TEXTS_PATH, exist_ok=True)
        
        # Read the CSV data properly
        try:
            csv_data = pd.read_csv(io.BytesIO(csv_file.read()))
            st.dataframe(data=csv_data)
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")    
    
    globals['UPLOADED_DATA_NAME'] = csv_file.name
    PREPROCESS_CHECKPOINT = True
    st.success(body=f'SUCCESS: Confirmed directory path. {"CSV has changed since last load." if source_changed else "Same CSV as last load."}')


def load_cb():
    preprocess_texts()
    DOC_TERM_MATRIX = doc_term_matrix()
    globals['DOC_TERM_MATRIX'] = DOC_TERM_MATRIX

def query_cb():
    DOC_TERM_MATRIX = globals['DOC_TERM_MATRIX']
    VOCABULARY = globals['VOCABULARY']
    query_input = globals['query_input']
    # Lemmatize the query with performance tracking
    start_time = time.time()
    normalized_text = cltk_normalize(text=query_input)
    tokens = [token for token in normalized_text.split()]
    kws = lemmatizer.lemmatize(tokens=tokens)
    lemmatize_time = time.time() - start_time
    
    # Log performance data
    if DEBUG:
        token_count = len(tokens)
        logger.debug(f"Query lemmatization: {token_count} tokens in {lemmatize_time:.4f}s ({token_count/lemmatize_time:.1f} tokens/sec)")
        # Log cache stats
        if hasattr(lemmatizer, 'stats'):
            hits = lemmatizer.stats.get("hits", 0)
            misses = lemmatizer.stats.get("misses", 0)
            total = hits + misses
            hit_rate = (hits / total) * 100 if total > 0 else 0
            logger.info(f"Lemmatizer cache stats: {hit_rate:.1f}% hit rate ({hits} hits, {misses} misses)")
    vocab_indexes =np.asarray(a=sorted(list(filter(lambda x: x is not None, [VOCABULARY.get(kw) for kw in kws]))))

    if DEBUG:
        st.write(f'vocab_indexes:\n{vocab_indexes}')

    dtm_df = pd.DataFrame(data=DOC_TERM_MATRIX)
    
    if DEBUG:
        st.write('Column-reduced DTM')
        st.dataframe(data=dtm_df.iloc[:, vocab_indexes].any(axis=1))

#endregion

# OTHER FUNCTIONS
#region
def doc_term_matrix():
    global DTM_CHECKPOINT
    PREPROCESSED_TEXTS_PATH = globals['PREPROCESSED_TEXTS_PATH']
    
    # Log start of matrix creation
    logger.info("Starting document-term matrix creation")
    
    # Validity checks
    if not DTM_CHECKPOINT:
        logger.warning("DTM checkpoint not reached. Skipping matrix creation.")
        return
    
    # Check for existence of required directories
    if not os.path.exists(path=PREPROCESSED_TEXTS_PATH):
        logger.error(f"Preprocessed directory does not exist: {PREPROCESSED_TEXTS_PATH}")
        st.error(body='ERROR (DOC_TERM_MATRIX): Directory containing preprocessed files does not exist.')
        return
    
    # Check for preprocessed files
    preprocessed_files = os.listdir(path=PREPROCESSED_TEXTS_PATH)
    if len(preprocessed_files) == 0:
        logger.warning(f"No documents found in {PREPROCESSED_TEXTS_PATH}")
        st.warning(body='WARNING (DOC_TERM_MATRIX): No documents have been preprocessed yet.')
        return None
    
    # Cache key for document term matrix
    cache_key = f"dtm_{PREPROCESSED_TEXTS_PATH}_{len(preprocessed_files)}"
    
    # Check if DTM is cached
    if USE_CACHE and cache.has(cache_key):
        logger.info("Using cached document-term matrix")
        cache_data = cache.get(cache_key)
        if isinstance(cache_data, dict) and 'dtm' in cache_data and 'vocabulary' in cache_data:
            globals['VOCABULARY'] = cache_data['vocabulary']
            st.text(f'Vocabulary size (from cache): {len(cache_data["vocabulary"])}')            
            st.success("Document-term matrix loaded from cache")
            return cache_data['dtm']
    
    # Create progress indicator
    progress_text = st.empty()
    progress_text.text("Building document-term matrix...")
    progress_bar = st.progress(0.0)
    
    # Start timer
    start_time = time.time()
    
    # Update paths to include full path
    progress_text.text("Collecting preprocessed files...")
    preprocessed_txt_paths = [os.path.join(PREPROCESSED_TEXTS_PATH, file_name) 
                             for file_name in preprocessed_files 
                             if file_name.endswith('.txt')]    
    
    # Create vectorizer
    progress_text.text("Initializing vectorizer...")
    progress_bar.progress(0.2)
    vectorizer = CountVectorizer(input='filename')
    
    # Fit and transform
    progress_text.text(f"Processing {len(preprocessed_txt_paths)} documents...")
    progress_bar.progress(0.4)
    
    try:
        X = vectorizer.fit_transform(raw_documents=preprocessed_txt_paths)
        progress_bar.progress(0.8)
        
        # Store vocabulary
        globals['VOCABULARY'] = vectorizer.vocabulary_
        vocab_size = len(vectorizer.vocabulary_)
        logger.info(f"Created document-term matrix with vocabulary size: {vocab_size}")
        st.text(f'Vocabulary size: {vocab_size}')
        
        # Convert to array
        dtm_array = X.toarray()
        
        # Cache the results
        if USE_CACHE:
            cache_data = {
                'dtm': dtm_array,
                'vocabulary': vectorizer.vocabulary_
            }
            cache.set(cache_key, cache_data)
            logger.info("Document-term matrix saved to cache")
        
        # Show completion
        elapsed_time = time.time() - start_time
        progress_text.text(f"Document-term matrix created in {elapsed_time:.2f} seconds")
        progress_bar.progress(1.0)
        
        return dtm_array
        
    except Exception as e:
        logger.error(f"Error creating document-term matrix: {str(e)}")
        st.error(f"Error creating document-term matrix: {str(e)}")
        progress_bar.progress(0)
        progress_text.text("Document-term matrix creation failed!")
        return None

def preprocess_texts():
    global PREPROCESS_CHECKPOINT
    global DTM_CHECKPOINT
    DTM_CHECKPOINT = False
    FULL_TEXTS_PATH = globals['FULL_TEXTS_PATH']
    PREPROCESSED_TEXTS_PATH = globals['PREPROCESSED_TEXTS_PATH']
    
    # Log start of preprocessing
    logger.info(f"Starting text preprocessing from {FULL_TEXTS_PATH}")
    
    # Validity checks
    if not PREPROCESS_CHECKPOINT:
        logger.warning("Preprocessing checkpoint not reached. Skipping preprocessing.")
        return
    
    if FULL_TEXTS_PATH is None or not os.path.exists(path=FULL_TEXTS_PATH):
        logger.error(f"Directory path does not exist: {FULL_TEXTS_PATH}")
        st.error(body='ERROR (PREPROCESS): Directory path for dataset does not exist.')
        return
    
    # Create preprocessing directory if it doesn't exist
    os.makedirs(name=PREPROCESSED_TEXTS_PATH, exist_ok=True)
    
    # Get list of files to process
    file_list = os.listdir(path=FULL_TEXTS_PATH)
    total_files = len(file_list)
    
    # Create progress bars
    progress_text = st.empty()
    progress_text.text(f"Preprocessing {total_files} files...")
    prog = st.progress(value=0.0)
    
    # Create processing timer
    start_time = time.time()
    processed_count = 0
    error_count = 0
    cached_count = 0
    
    # Process each file
    for index, filename in enumerate(file_list):
        try:
            # Update progress
            progress_pct = float(index) / total_files
            prog.progress(value=progress_pct)
            
            # Skip non-text files
            if not filename.endswith('.txt'):
                logger.warning(f"Skipping non-text file: {filename}")
                continue
                
            # Generate output filename
            output_filename = filename.split(sep='.txt')[0] + '_preprocessed.txt'
            output_path = os.path.join(PREPROCESSED_TEXTS_PATH, output_filename)
            
            # Check if file is already cached
            cache_key = f"preprocessed_{FULL_TEXTS_PATH}_{filename}"
            
            if USE_CACHE and cache.has(cache_key) and not os.path.exists(output_path):
                # Retrieve from cache and save to file
                logger.debug(f"Using cached preprocessed text for {filename}")
                lemmatized_blob = cache.get(cache_key)
                with open(file=output_path, mode='w') as preprocessed_file:
                    preprocessed_file.write(lemmatized_blob)
                cached_count += 1
            else:
                # Process the file
                input_path = os.path.join(FULL_TEXTS_PATH, filename)
                
                # Read and normalize the text
                with open(file=input_path, mode='r', encoding='utf-8', errors='replace') as f:
                    text = f.read()
                    
                text = cltk_normalize(text=text)
                
                # Display current file in UI
                current_info = f"Processing file {index+1}/{total_files}: {filename}"
                progress_text.text(current_info)
                
                # Lemmatize text with performance logging
                start_time = time.time()
                lemmatized_tokens = lemmatizer.lemmatize(tokens=text.split())
                lemmatize_time = time.time() - start_time
                
                # Extract lemmas and join them
                lemmatized_blob = ' '.join(list([pair[1] for pair in lemmatized_tokens]))
                
                # Log performance stats
                if DEBUG:
                    token_count = len(text.split())
                    logger.debug(f"Lemmatized {token_count} tokens in {lemmatize_time:.4f}s ({token_count/lemmatize_time:.1f} tokens/sec)")
                
                # Save preprocessed file
                with open(file=output_path, mode='w', encoding='utf-8') as preprocessed_file:
                    preprocessed_file.write(lemmatized_blob)
                    
                # Cache the result
                if USE_CACHE:
                    cache.set(cache_key, lemmatized_blob)
            
            processed_count += 1
            
            # Update progress for this file
            prog.progress(value=float(index + 1) / total_files)
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing file {filename}: {str(e)}")
            if DEBUG:
                st.error(f"Error processing {filename}: {str(e)}")
    
    # Compute processing statistics
    elapsed_time = time.time() - start_time
    logger.info(f"Preprocessing completed. Processed {processed_count} files in {elapsed_time:.2f} seconds.")
    logger.info(f"Cached: {cached_count}, Errors: {error_count}")
    
    # Update final progress
    progress_text.text(f"Preprocessing complete! Processed {processed_count} files in {elapsed_time:.2f} seconds.")
    prog.progress(value=1.0)
    
    # Set checkpoints
    PREPROCESS_CHECKPOINT = False
    DTM_CHECKPOINT = True
    
    # Show success message
    st.success(f"Successfully preprocessed {processed_count} files. Ready to create document-term matrix.")
#endregion