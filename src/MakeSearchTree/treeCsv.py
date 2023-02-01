import pandas as pd 
#first get the csv 
path = "input/csvin.csv"
out = "ouput/newTree.csv"
col = ["Section ID"]
df = pd.read_csv(path, usecols = col, header = 0)
#for each row get the name of the file until .xml
count = 0
titles = {}
newCol = []
for index, val in df.iterrows():
    temp = val.get(0)
    #returns the file name
    temp = temp.partition('.xml')[0]
    if(temp not in titles):
        titles[temp] = count
        count += 1
        if count%100 == 0:
            print(count)
#2nd iteration adds the new number to the code 
for index, val in df.iterrows():
    temp = val.get(0)
    before = temp.partition('.xml')[0]
    after = temp.partition('.xml')[2]
    after = str(titles[before]) + '-' + after
    newCol.append(after)
df["TreePath"] = newCol 
df.to_csv(out)
print("done")