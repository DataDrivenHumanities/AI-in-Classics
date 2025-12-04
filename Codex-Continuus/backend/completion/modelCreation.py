import numpy as np
import tensorflow as tf
import os
import re
from sklearn.model_selection import train_test_split

#important model variables
dimensionality = 64
sequenceLength = 32
numHeads = 16
batchSize = 32
numEpochs = 25

def getSeqLen(): 
    return sequenceLength
#corpus data
corpusPath = "trainingData/latinCorpus.txt"
cleanCorpusPath = "trainingData/latinCorpusCleaned.txt"

#grabbing/cleaning corpus data
def readAndCleanInput():
    text = ""
    print("-----Reading and Cleaning Input Text-----")
    with open(corpusPath, 'r', encoding='utf-8') as f:
        tempText = f.read()
    for char in tempText:
        if not char.isnumeric():
            if char.isalpha() or char == ' ' or char == '.' or char == '?' or char =='!' or char == ',' or char == ';' or char == '-':
                text += char
    text = re.sub(r"\s+", " ", text)
    with open(cleanCorpusPath, "w") as f:
        f.write(text)
        
#throw exception if corpus is not found
if not os.path.exists(corpusPath):
    raise ValueError("Error: Could not find file containing corpus data at trainingData/latinCorpus.txt")

processInput = False
if not os.path.exists(cleanCorpusPath):
    #by default, if there is not a cleaned txt file, this needs to be true
    processInput = True
if processInput:
    readAndCleanInput()
text = ""
with open(cleanCorpusPath, 'r', encoding = 'utf-8') as f:
    text = f.read()

#important variables from the corpus data
vocab = sorted(set(text))
vocabSize = len(vocab)
#encoding and decoding
charToInt = {ch: i for i, ch in enumerate(vocab)}
intToChar = {i: ch for i, ch in enumerate(vocab)}

#its a bit more clear to have this as a function
def decode(encodedChar):
    return intToChar[encodedChar]

#pads out to 32 char long, encodes string text, adds location info, and a batch dimension to match the model input
def sequenceToInputFormat(text):
    temp = ""
    for c in text:
        if c in vocab:
            temp += c
    text = temp
    if(len(text) > sequenceLength):
        raise ValueError(f"The method 'modelCreation.stringToInputFormat' expects an input equal to or smaller than the sequnce length: {sequenceLength}\n Handle splitting larger text bodies into sequences at the callsite.")
    pad = ""
    for i in range(sequenceLength - len(text)):
        pad += ' '
    text = pad + text
    encodedText = np.array([charToInt[c] for c in text])
    location = np.linspace(start = -1.0, stop = 1.0, num = sequenceLength)
    encodedText = np.stack([encodedText, location], axis=-1)

    encodedText = np.expand_dims(encodedText, axis=0)
    return encodedText

#converts text into integers
encodedText = np.array([charToInt[c] for c in text])
location = np.linspace(start = -1.0, stop = 1.0, num = sequenceLength)
x = []
y = []
for i in range(len(encodedText) - sequenceLength - 1):
    charSeq = encodedText[i: i+sequenceLength]
    target = encodedText[i+sequenceLength+1]
    
    charSeqWithLocation = np.stack([charSeq, location], axis=1)
    x.append(charSeqWithLocation)
    y.append(target)

#split into train and validation data
splitInd = int(len(x) * 0.8)
xTrain, xValid = x[:splitInd], x[splitInd:]
yTrain, yValid = y[:splitInd], y[splitInd:]

#convert into tensorflow dataset objects
trainDataset = tf.data.Dataset.from_tensor_slices((xTrain, yTrain)).batch(batchSize)
trainDataset.shuffle(buffer_size=5000)
trainDataset.prefetch(tf.data.AUTOTUNE)
validDataset = tf.data.Dataset.from_tensor_slices((xValid, yValid)).batch(batchSize)

#call this from an external callsite if necessary, to load the model, use model.load()
def trainAndSaveModel():
    #multihead attension block, residual connection, and normalization
    inlayer = tf.keras.Input(shape = (sequenceLength,2))
    projection = tf.keras.layers.Dense(units = dimensionality)(inlayer)
    multiHeadAttention = tf.keras.layers.MultiHeadAttention(num_heads = numHeads, key_dim = dimensionality)(projection, projection, projection)
    residual = tf.keras.layers.Add()([projection, multiHeadAttention])
    normalized = tf.keras.layers.LayerNormalization()(residual)

    #feed forward block, residual connection, and normalization
    feedForwardA = tf.keras.layers.Dense(units = dimensionality, activation = tf.keras.activations.relu)(normalized)
    feedForwardB = tf.keras.layers.Dense(units = dimensionality)(feedForwardA)
    residualB = tf.keras.layers.Add()([normalized, feedForwardB])
    normalizedB = tf.keras.layers.LayerNormalization()(residualB)

    #output layer
    flat = tf.keras.layers.Flatten()(normalizedB)
    outlayer = tf.keras.layers.Dense(units = vocabSize, activation = tf.keras.activations.softmax)(flat)

    #model creation
    model = tf.keras.Model(inputs = inlayer, outputs = outlayer)
    model.summary()
    model.compile(optimizer = tf.keras.optimizers.Adam(), loss = tf.keras.losses.SparseCategoricalCrossentropy(), metrics = ['accuracy'])
    model.fit(trainDataset, epochs = 20, validation_data = validDataset)
    model.save('generator.keras')