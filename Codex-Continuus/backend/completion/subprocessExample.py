import subprocess
import sys
from pathlib import Path

#path to the venv that completion.py expects to run in
venv = Path("transformerEnv/bin/python")
#path to the script, change these paths if necessary since they are relative paths
script = Path("completion.py")

#command line args for completion.py, make sure all are of type string
exampleOCRText = "sacra, quae Cronia esse iterantur ab illis, eumque diem celebrant per agros urbesque fere omnes exercent epulas laeti famulosque procurant quisque suos"
exampleThreshold = "1/32"

#The result of this subprocess will be the returned value from completion.textCorrection() 
#getting printed on the command line via stdout. Below, I use result.stdout.strip() to get this value

result = subprocess.run(
    [venv, script, exampleOCRText, exampleThreshold],
    capture_output= True,
    text= True
)

print(f"Result from completion step: {result.stdout.strip()}")