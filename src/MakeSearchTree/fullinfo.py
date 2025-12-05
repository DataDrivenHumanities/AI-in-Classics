import pandas as pd

newRow = "ouput/newTree.csv"
input = "input/csvin.csv"
out = "ouput/fullInfoNewTree"
col = ["TreePath"]
df = pd.read_csv(input)
df2 = pd.read_csv(newRow, usecols=col)
seriesmode = df2["TreePath"].values
df["TreePath"] = seriesmode
df.to_csv(out)
print("done")
