import tensorflow as tf
import numpy as np
import modelCreation
import argparse 
from fractions import Fraction
model = tf.keras.models.load_model('generator.keras')
model.compile()
sequenceLength = modelCreation.getSeqLen()
#this variable represents the maximum number of missing characters can be generated at each position in the text
depth = 5
def test():
    testSeq = "s"
    testSeq = modelCreation.sequenceToInputFormat(testSeq)
    probDist = model(testSeq)[0]
    threshold = 1/32
    for i in range(0,len(probDist)):
        if probDist[i] >= threshold:
            print(f"{modelCreation.decode(i)}: {probDist[i]}")

def getNextCharsVector(probDist, threshold):
    nextChars = []
    for j in range(0,len(probDist)):
        probability = probDist[j]
        char = modelCreation.decode(j)
        if probability >= threshold:
            nextChars.append((char,probability))
    nextCharsSorted = [ch for ch, p in sorted(nextChars, key=lambda x: x[1], reverse=True)]
    return nextCharsSorted

def getSeqeunce(text, i, threshold):
    sequence = modelCreation.sequenceToInputFormat('')
    sequenceText = ''
    if(i < sequenceLength):
        threshold = (threshold * i) / sequenceLength
        sequenceText = text[:i]
        sequence = modelCreation.sequenceToInputFormat(sequenceText)
    else:
        sequenceText = text[i-sequenceLength:i]
        sequence = modelCreation.sequenceToInputFormat(sequenceText)
    return sequence, sequenceText, threshold
        
def textCorrection(text, thresholdStatic):
    #iterate over whole text, text can be appended to during the run, so we assume the largest possible length
    for i in range(1,len(text) *  depth):
        #since len(text) can change
        if i >= (len(text)-1):
            break
        #gather the sequence (and adjusted threshould value for short seqeunces) from the text
        sequence, sequenceText, threshold = getSeqeunce(text, i, thresholdStatic)

        #probDist is a map of all characters in the vocab and their normalized probability
        probDist = model(sequence)[0]

        #get next chars vector- all characters with prob above threshold, and the highest probable char
        nextChars = getNextCharsVector(probDist, threshold)
        maxChar = nextChars[0]

        if text[i] not in nextChars:
            #actual character (test[i]) not found in nextChars vector, replace it somehow...
            #--- naive strategy ---
            #text = text = text[:i] + maxChar + text[i+1:]
            #continue
            #---

            #in depth strategy--- 

            #first, the char after will be used to check replacement strategies
            followingChar = ' '
            if (i+1) < len(text):
                followingChar = text[i+1] 
            
            #print(f"text: {text}, wrong char: {text[i]}, next chars: {nextChars}, following char: {followingChar}")
            #1. test for 'case a' error- text[i] is misinterpreted and should be replaced
            caseA = False
            for char in nextChars:
                testSequence = modelCreation.sequenceToInputFormat(sequenceText[1:] + char)
                print(sequenceText[1:] + char)
                probDist = model(testSequence)[0]
                testNextChars = getNextCharsVector(probDist, threshold)
                if followingChar in testNextChars:
                    text = text[:i] + char + text[i+1:]
                    caseA = True
                    break
            if caseA: continue
            #2. test for 'case b' error- text[i] is extraneous and should be skipped
            if followingChar in nextChars:
                text = text[:1] + text[i+1:]
                continue
            
            #3. test for 'case c' error- text[i] is early and should come after some missing text
            for j in range (0,5):
                seqeunceText = sequenceText[1:] + maxChar
                testSequence = modelCreation.sequenceToInputFormat(sequenceText[1:] + maxChar)
                probDist = model(testSequence)[0]
                nextChars, maxChar = getNextCharsVector(probDist, threshold)
                if text[i] in nextChars:
                    text = text[:i] + maxChar + text[i:]
                    break
                else:
                    text = text[:i] + maxChar + text[i+1:]
                    i += 1
            
    return text

#Example run
#print(textCorrection("Maxima pars Graium Saturno et maxKme AthKnae", 0.001))
#exit()
#this file is called on from the CLI using subprocess. in that instance, the value of __name__ is '__main__'
#it must be called using subprocess, as it expects the source to be the 'backend/completion/transformerEnv/' interpreter or venv

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ocrText", default = "Provide OCRtext as a CLI argument")
    parser.add_argument("threshold", default = "1/32")
    args = parser.parse_args()

    threshold = args.threshold
    try:
        if '/' in threshold:
            threshold = float(Fraction(threshold))
        else:
            threshold = float(threshold)
    except (ValueError, ZeroDivisionError) as e:
        raise ValueError(f"Invalid threshold value '{threshold}'. Write the threshold value as a string either as a fraction like '1/32' or a decimal like '0.03': {e}")
        
    correctedText = textCorrection(args.ocrText, threshold)
    print(correctedText)
    #subprocess will capture this output