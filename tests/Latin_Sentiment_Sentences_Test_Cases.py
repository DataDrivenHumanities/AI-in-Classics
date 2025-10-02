import requests
import json
import string
import time
from typing import List, Dict

# Configuration for the Ollama server
OLLAMA_API_URL = (
    "http://localhost:11434/api/generate"  # Edit this with your Ollama server IP
)
OLLAMA_MODEL = "latin_model:1.0.0"  # The model used for sentiment analysis

# Dataset of Latin sentences with expected sentiment and English translations
LATIN_DATA: List[Dict[str, str]] = [
    {
        "sentence": "Caelum pulchrum est.",
        "sentiment": "positive",
        "translation": "The sky is beautiful.",
    },
    {
        "sentence": "Puer discipulus malus est.",
        "sentiment": "negative",
        "translation": "The boy is a bad student.",
    },
    {
        "sentence": "Copiae amiserunt bellum.",
        "sentiment": "negative",
        "translation": "The troops lost the war.",
    },
    {
        "sentence": "Pater laudabat filium.",
        "sentiment": "positive",
        "translation": "The father was praising his son.",
    },
    {
        "sentence": "Marcus Brutus tradidit suum amicum.",
        "sentiment": "negative",
        "translation": "Marcus Brutus betrayed his friend.",
    },
    {
        "sentence": "Ego optimus miles eram.",
        "sentiment": "positive",
        "translation": "I was the best student",
    },
    {
        "sentence": "Quae scelera videmus?",
        "sentiment": "negative",
        "translation": "What evil deed do we see?",
    },
    {
        "sentence": "Malum consilium est.",
        "sentiment": "negative",
        "translation": "The plan is bad",
    },
    {
        "sentence": "Sum amicus eius",
        "sentiment": "positive",
        "translation": "I am his friend",
    },
    {
        "sentence": "Brutus te laudavit",
        "sentiment": "positive",
        "translation": "Brutus praised you",
    },
    {
        "sentence": "Patria delebatur",
        "sentiment": "negative",
        "translation": "The country was being destroyed",
    },
    {
        "sentence": "Domus ustus erat.",
        "sentiment": "negative",
        "translation": "The home had been burned down.",
    },
    {
        "sentence": "Gladiator praemium vicit.",
        "sentiment": "positive",
        "translation": "The gladiator won a prize.",
    },
    {
        "sentence": "Vita eius erat nimis brevis.",
        "sentiment": "negative",
        "translation": "Her life was too brief.",
    },
    {
        "sentence": "Panis fuit bonus.",
        "sentiment": "positive",
        "translation": "The bread was good.",
    },
    {
        "sentence": "Post paucas horas Caesar Asiam cepit",
        "sentiment": "negative",
        "translation": "After a few hours, Caesar captured Asia.",
    },
    {
        "sentence": "Mater beatum infantem bene curat.",
        "sentiment": "positive",
        "translation": "The mother cares well for the fortunate baby.",
    },
    {
        "sentence": "Imperator non curat de salute suae nationis.",
        "sentiment": "negative",
        "translation": "The emperor does not care for the safety of his own people.",
    },
    {
        "sentence": "Mater paterque suos pueros neglexerunt.",
        "sentiment": "negative",
        "translation": "The mother and father neglected their children.",
    },
    {
        "sentence": "Puer miser ab animali saevo necatus erat.",
        "sentiment": "negative",
        "translation": "The poor boy had been killed by a savage animal.",
    },
    {
        "sentence": "Venator ursam post longam pugnam necavit.",
        "sentiment": "negative",
        "translation": "The hunter killed the bear after a long battle.",
    },
    {
        "sentence": "Post redierunt Romam, nautae usi sunt otium.",
        "sentiment": "positive",
        "translation": "After they returned to Rome, the sailors enjoyed leisure time.",
    },
    {
        "sentence": "Puella est laeta videre suum fratrem minorem.",
        "sentiment": "positive",
        "translation": "The girl is happy to see her younger brother.",
    },
    {
        "sentence": "Navis confractus est ab hostibus Romae.",
        "sentiment": "negative",
        "translation": "The ship was broken by the enemies of Rome",
    },
    {
        "sentence": "Heros erat qui multos cives servavit.",
        "sentiment": "positive",
        "translation": "He was a hero who saved many citizens.",
    },
    {
        "sentence": "Urbs ab hostibus malis victa deletaque est.",
        "sentiment": "negative",
        "translation": "The city was conquered and destroyed by the wicked enemy.",
    },
    {
        "sentence": "Magna facta discipulorum eius magistro veteri placuerunt.",
        "sentiment": "positive",
        "translation": "The great achievements of his students pleased the old teacher.",
    },
    {
        "sentence": "Puellae iuveni curiosaeque libet in agros migrare.",
        "sentiment": "positive",
        "translation": "The young and curious girl likes to wander into fields.",
    },
    {
        "sentence": "Sol ita lucet ut fruges celeriter crescant.",
        "sentiment": "positive",
        "translation": "The sun shines in such a way that the crops grow quickly.",
    },
    {
        "sentence": "Imperator iussit milites interficere sine misericordia.",
        "sentiment": "negative",
        "translation": "The emperor ordered the soldiers to kill without mercy.",
    },
    {
        "sentence": "Princeps sensit fas suum custodire patriam.",
        "sentiment": "positive",
        "translation": "The ruler felt it was his sacred duty to protect his country.",
    },
    {
        "sentence": "Amici Scipionis invitaverunt ad cenam post victoriam magnam vixit.",
        "sentiment": "positive",
        "translation": "Scipio's friends invited him to dinner after he won a great victory.",
    },
    {
        "sentence": "Vir egit gratias Venerem uxori pulchrae et Iunonem liberis.",
        "sentiment": "positive",
        "translation": "The man gave thanks to Venus for his beautiful wife and to Juno for his children.",
    },
    {
        "sentence": "Sceleratus vehemens expulsus erat sicut poena vitae vitiosae.",
        "sentiment": "negative",
        "translation": "The violent criminal was exiled as punishment for a life full of vice.",
    },
    {
        "sentence": "Fabulae a patre eorum narratae sororem fratremque oblectaverunt.",
        "sentiment": "positive",
        "translation": "The stories told by their father delighted the brother and sister.",
    },
    {
        "sentence": "Cupiditate aeterna devotus, desidero aliquam quae non desiderat me.",
        "sentiment": "negative",
        "translation": "Accursed by eternal longing, I long for someone who does not long for me.",
    },
    {
        "sentence": "Cum peste adfecti essent, boves iam moriebantur.",
        "sentiment": "negative",
        "translation": "Since they had been afflicted by the plague, the cows soon died.",
    },
    {
        "sentence": "Puella puero nervoso dixit se reddere amorem eius.",
        "sentiment": "positive",
        "translation": "The girl told the nervous boy that she returned his love.",
    },
    {
        "sentence": "Cum bellum tandem vicissent, cives magno gaudio celebrabant.",
        "sentiment": "positive",
        "translation": "When at last they had won the war, the citizens celebrated with great joy.",
    },
    {
        "sentence": "Umbra uxoris mortuae illum miserum ita persequitur ut otium numquam reperiat.",
        "sentiment": "negative",
        "translation": "The ghost of his dead wife haunts that wretched man so that he will never find peace.",
    },
    {
        "sentence": "Cum nemo audiat, poeta tristis queritur dominam eum relinquisse.",
        "sentiment": "negative",
        "translation": "Although no one is listening, the sad poet laments that his mistress has abandoned him.",
    },
    {
        "sentence": "Bono nuntio accepto, nuntius delectatus civibus nuntiat opem iam adventuram esse.",
        "sentiment": "positive",
        "translation": "With the good news having been received, the delighted messenger announces to the citizens that aid will soon arrive.",
    },
    {
        "sentence": "Vulgus surrexerunt fores aedis, necatatum et consauciatum multos.",
        "sentiment": "negative",
        "translation": "The mob surged the gates of the temple, killing and injuring many.",
    },
    {
        "sentence": "Canes denique invenerunt aprum post diem longum et miserum ita venatores id potuerunt necare",
        "sentiment": "negative",
        "translation": "The dogs finally found the boar after a long, miserable day outside so the hunters could kill it.",
    },
    {
        "sentence": "Quod ea voluerat fratrem tam diu, puella celebravit quando mater peperit iterum.",
        "sentiment": "positive",
        "translation": "Because she had wanted a brother for such a long time, the girl celebrated when her mother gave birth again.",
    },
    {
        "sentence": "In oratone, orator optimus fuit et igitur multas coronas laurinas vicit.",
        "sentiment": "positive",
        "translation": "In his speech, the orator was the best and accordingly, he won many wreaths of laurel.",
    },
    {
        "sentence": "Stultitiast, mater, venatum ducere invitas canes",
        "sentiment": "negative",
        "translation": "It is foolish, mother, to lead the unwilling dogs to the hunt",
    },
    {
        "sentence": "Si quis metuens vivet, liber mihi non erit umquam",
        "sentiment": "negative",
        "translation": "If anyone lives in fear, he will not ever be free - in my opinion",
    },
    {
        "sentence": "imperator promisit decem milia militum celerrime discessura esse, dummodo satis copiarum reciperent.",
        "sentiment": "positive",
        "translation": "The general promises ten thousand soldiers to depart most quickly, so long as they receive satisfactory supplies.",
    },
    {
        "sentence": "Cum cūrā docet ut discipulī bene discant",
        "sentiment": "positive",
        "translation": "He teaches them with care so the students may learn well",
    },
]


def clean_sentiment(text: str) -> str:
    cleaned = text.strip().lower().rstrip(string.punctuation + string.whitespace)
    return cleaned


# Check if the Ollama server is reachable
def check_server() -> bool:

    try:
        response = requests.get(OLLAMA_API_URL.replace("api/generate", ""), timeout=5)
        response.raise_for_status()
        print("Ollama server is reachable.")
        return True
    except Exception as e:
        print(f"Failed to connect to Ollama server at {OLLAMA_API_URL}: {str(e)}")
        return False


def query_ollama(sentence: str, retries: int = 2) -> tuple[str, str]:
    prompt = f"{sentence}'. Respond with only 'positive' or 'negative'."
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    last_raw = ""
    for attempt in range(retries + 1):
        try:
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
            response.raise_for_status()
            result = json.loads(response.text)
            raw_output = result.get("response", "").strip()
            cleaned = clean_sentiment(raw_output)
            if cleaned in ["positive", "negative"]:
                return cleaned, raw_output
            elif cleaned != "":
                return cleaned, raw_output
            last_raw = raw_output
            print(
                f"Empty or invalid response, retrying attempt {attempt + 1}/{retries + 1}"
            )
        except Exception as e:
            last_raw = f"Error: {str(e)}"
            print(
                f"Request failed, retrying attempt {attempt + 1}/{retries + 1}: {str(e)}"
            )
        # Wait 1 second before retrying
        if attempt < retries:
            time.sleep(1)
    return "error", last_raw


def run_tests(test_cases: List[Dict[str, str]] = None):
    if test_cases is None:
        test_cases = LATIN_DATA
    total = len(test_cases)
    passed = 0
    failed = 0

    # Check server before running tests
    if not check_server():
        print("Aborting tests due to server connectivity issues.")
        return

    print("=== Latin Sentiment Analysis Test Suite ===")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Total Test Cases: {total}")
    print(f"Ollama Server: {OLLAMA_API_URL}")
    print("-" * 80)

    for idx, item in enumerate(test_cases, start=1):
        sentence = item["sentence"]
        expected = clean_sentiment(item["sentiment"])
        translation = item["translation"]

        predicted, raw_response = query_ollama(sentence, retries=2)

        # Add a delay between requests to avoid overwhelming the server
        time.sleep(1)

        if predicted == expected:
            status = "PASSED"
            passed += 1
        elif predicted == "error":
            status = "ERROR"
            failed += 1
            print(f"Ollama Response: {raw_response}")
        else:
            status = "FAILED"
            failed += 1

        display_pred = predicted.upper() if predicted != "error" else "ERROR"
        display_exp = expected.upper()

        print(f"Test {idx}/{total}:")
        print(f"  Sentence: {sentence}")
        print(f"  Translation: {translation}")
        print(f"  Expected: {display_exp}")
        print(f"  Predicted: {display_pred}")
        if predicted != expected:
            print(f"  Raw Ollama Response: {raw_response}")
        print(f"  Status: {status}")
        print("-" * 80)

    accuracy = (passed / total) * 100 if total > 0 else 0
    print("=== Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Accuracy: {accuracy:.2f}%")
    print("==================")


if __name__ == "__main__":
    run_tests()
