### SETUP
install uv
https://docs.astral.sh/uv/getting-started/installation/#__tabbed_1_2
run this in root
```
uv venv --python 3.12
uv pip install -r requirements.txt
```
### INFO
built using wsl 24.04 ubuntu python 3.12

to download input models and sample data run the download.py script
`uv run src/latin_bert/_0_download`

to train the model use the train script make sure to use the correct base model
`uv run src/latin_bert/_1_train.py`

to evaluate the model use the eval script make sure that the correct model folder is selected
`uv run src/latin_bert/_2_download.py`

output models can be found here
https://drive.google.com/drive/u/1/folders/1VBEvQYzIQjXGbxdLxNgpYzvc5Xk41vDj



DATASET

latin sentiment analysis
1 postive
0 negative
2 neutral


Train 4
INPUT PROMPT
```
Give me the largest set of grammatically complex latin sentences that you can. Ensure that they are unique and varied in content and make them balanced and contain things like negations and diffrent parts of speech as well

indirect positive associations and pleasnt imagery
{"sentence": "Amicitia vera vitam ornat.", "label": 1}
{"sentence": "Hoc bellum malum et crudele est.", "label": 0}

latin sentiment analysis
1 postive
0 negative
2 neutral
```
claude sonnet 4.6 Thinking
gemini 3.1 Thinking
chatgpt default
claude sonnet 4.6 Thinking
deepseek v3.2 Deep Think
