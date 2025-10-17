import requests
import json
import string
import time
import re
from typing import List, Dict

# Configuration for the Ollama server
OLLAMA_API_URL = (
    "http://localhost:11434/api/generate"  # Edit this with your Ollama server IP
)
=======
OLLAMA_MODEL = "LatinSentimentAnalysis:latest"  # Updated to match loaded model
OLLAMA_TAGS_URL = OLLAMA_API_URL.replace(
    "/api/generate", "/api/tags"
)  # Endpoint to check models
OLLAMA_PULL_URL = OLLAMA_API_URL.replace(
    "/api/generate", "/api/pull"
)  # Endpoint to pull model
>>>>>>> Stashed changes


# Load test cases from JSON file
def load_test_cases(
    file_path: str = "LatinSentenceTestDatav2.json",
) -> List[Dict[str, str]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Handle both array and {"test_cases": [...]} structures
            test_cases = data if isinstance(data, list) else data.get("test_cases", [])
        return test_cases
    except Exception as e:
        print(f"Error loading test cases from {file_path}: {str(e)}")
        return []


def clean_sentiment(text: str) -> str:
    cleaned = text.strip().lower().rstrip(string.punctuation + string.whitespace)
    if len(cleaned.split()) > 1:  # More than one word
        print(f"WARNING: Extra text detected: {text}")
    return cleaned.split()[0] if cleaned else ""  # Take first word only


def parse_sentiment_detailed(raw_output: str) -> dict:
    """
    Parse "SENTIMENT RESULTS: [full label]" into components.
    More flexible to handle variations like missing score or different phrasing.
    Returns dict with 'full_label', 'base_sentiment', 'intensity', 'score'.
    """
    # Flexible match for SENTIMENT RESULTS line
    match = re.search(
        r"SENTIMENT RESULTS:\s*(.+?)(?=\n|$)", raw_output, re.IGNORECASE | re.DOTALL
    )
    if not match:
        return {
            "full_label": None,
            "base_sentiment": None,
            "intensity": None,
            "score": None,
        }

    full_label = match.group(1).strip()

    # Parse base sentiment (POSITIVE/NEGATIVE/NEUTRAL) - more lenient
    base_match = re.search(r"(POSITIVE|NEGATIVE|NEUTRAL)", full_label, re.IGNORECASE)
    base_sentiment = base_match.group(1).upper() if base_match else None

    # Parse score (look for +1, -2, score -1, etc.)
    score_match = re.search(r"(?:score\s*)?([+-]?\d+)", full_label)
    score = int(score_match.group(1)) if score_match else 0

    # Parse intensity (EXTREMELY/VERY/MODERATELY) - optional
    intensity_match = re.search(
        r"(EXTREMELY|VERY|MODERATELY)", full_label, re.IGNORECASE
    )
    intensity = intensity_match.group(1).upper() if intensity_match else None

    return {
        "full_label": full_label,
        "base_sentiment": base_sentiment,
        "intensity": intensity,
        "score": score,
    }


# Preload the Latin model
def preload_model() -> bool:
    print(f"Attempting to preload model {OLLAMA_MODEL}...")

    # 1. Check if the model is already loaded
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=10)
        response.raise_for_status()
        models = json.loads(response.text).get("models", [])
        model_names = [model["name"] for model in models]
        if OLLAMA_MODEL in model_names:
            print(f"Model {OLLAMA_MODEL} is already loaded.")
            return True
    except Exception as e:
        print(f"Failed to check model status: {str(e)}")

    # 2. Pull the model to make sure it is available to use
    try:
        payload = {"name": OLLAMA_MODEL}
        response = requests.post(OLLAMA_PULL_URL, json=payload, timeout=120)
        response.raise_for_status()
        print(f"Model {OLLAMA_MODEL} pulled successfully.")
    except Exception as e:
        print(f"Failed to pull model {OLLAMA_MODEL}: {str(e)}")
        return False

    # Step 3: Send a test prompt to warm up the model
    try:
        test_prompt = "Test"
        payload = {"model": OLLAMA_MODEL, "prompt": test_prompt, "stream": False}
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=90)
        response.raise_for_status()
        print(f"Model {OLLAMA_MODEL} warmed up successfully.")
        return True
    except Exception as e:
        print(f"Failed to warm up model {OLLAMA_MODEL}: {str(e)}")
        return False


# Check if the Ollama server is reachable and preload model into memory
def check_server() -> bool:
    try:
        response = requests.get(OLLAMA_API_URL.replace("/api/generate", ""), timeout=10)
        response.raise_for_status()
        print("Ollama server is reachable.")
    except Exception as e:
        print(f"Failed to connect to Ollama server at {OLLAMA_API_URL}: {str(e)}")
        return False

    if not preload_model():
        print(f"Aborting tests due to failure to preload model {OLLAMA_MODEL}.")
        return False
    return True


def query_ollama(sentence: str, retries: int = 2) -> tuple[str, str]:
    prompt = sentence
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {  # Add options for stability
            "num_predict": 25,  # Limit output length
        },
    }

    last_raw = ""
    for attempt in range(retries + 1):
        try:
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=90)

            if response.status_code != 200:
                print(
                    f"DEBUG: Response text: {response.text}"
                )  # Server's error message
            response.raise_for_status()
            result = json.loads(response.text)
            raw_output = result.get("response", "").strip()
            cleaned = clean_sentiment(raw_output)
            if cleaned in ["positive", "negative", "neutral"]:
                return cleaned, raw_output
            elif cleaned != "":
                return cleaned, raw_output
            last_raw = raw_output
            print(
                f"Empty or invalid response, retrying attempt {attempt + 1}/{retries + 1}"
            )
        except requests.exceptions.HTTPError as e:
            last_raw = f"HTTP Error {e.response.status_code}: {e.response.text}"
            print(
                f"Request failed, retrying attempt {attempt + 1}/{retries + 1}: HTTP {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            last_raw = f"Error: {str(e)}"
            print(
                f"Request failed, retrying attempt {attempt + 1}/{retries + 1}: {str(e)}"
            )
        # Wait 2 seconds before retrying
        if attempt < retries:
            time.sleep(2)
    return "error", last_raw


def run_tests(test_cases: List[Dict[str, str]] = None):
    if test_cases is None:
        test_cases = load_test_cases()
    total = len(test_cases)
    passed = 0
    failed = 0

    # Start timing the entire test suite
    start_time = time.perf_counter()

    # Check server before running tests
    if not check_server():
        print("Aborting tests due to server or model issues.")
        return

    print("=== Latin Sentiment Analysis Test Suite ===")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Total Test Cases: {total}")
    print(f"Ollama Server: {OLLAMA_API_URL}")
    print("-" * 80)

    for idx, item in enumerate(test_cases, start=1):
        sentence = item["sentence"]
        expected_full = item.get("expected_sentiment", item.get("sentiment", ""))
        expected_base = (
            expected_full.split()[1] if " " in expected_full else expected_full.lower()
        )  # e.g., "POSITIVE" from "MODERATELY POSITIVE (+1)"
        expected_sign = (
            1 if "+" in expected_full else -1 if "-" in expected_full else 0
        )  # Direction
        translation = item["translation"]

        test_start = time.perf_counter()
        predicted, raw_response = query_ollama(sentence, retries=2)
        test_time = time.perf_counter() - test_start

        # Add a delay between requests to avoid overwhelming the server
        time.sleep(2)

        # Parse predicted sentiment
        parsed = parse_sentiment_detailed(raw_response)
        predicted_full = parsed["full_label"]
        predicted_base = parsed["base_sentiment"]
        predicted_score = parsed["score"]

        # Comparison logic
        if predicted_full == expected_full:
            status = "PASSED"
            passed += 1
        elif predicted_base == expected_base and (
            predicted_score > 0
            if expected_sign > 0
            else predicted_score < 0 if expected_sign < 0 else predicted_score == 0
        ):
            status = "PASSED (Intensity Variation)"
            passed += 1
            note = (
                "Note: Correct direction but intensity off (expected: "
                + expected_full
                + ", got: "
                + str(predicted_full)
                + ")"
            )
        else:
            status = "FAILED"
            failed += 1
            note = f"Wrong base/direction (expected: {expected_base}, got: {predicted_base})"

        display_pred = predicted_full or "EXTRACT FAILED"
        display_exp = expected_full

        print(f"Test {idx}/{total}:")
        print(f"  Sentence: {sentence}")
        print(f"  Translation: {translation}")
        print(f"  Expected: {display_exp}")
        print(f"  Predicted: {display_pred}")
        if status == "PASSED (Intensity Variation)":
            print(f"  {note}")
        if predicted_full != expected_full:
            print(f"  Raw Ollama Response: {raw_response[:200]}...")
        print(f"  Status: {status}")
        print(f"  Test Time: {test_time:.2f}s")
        print("-" * 80)

    # End timing and calculate duration
    end_time = time.perf_counter()
    total_time = end_time - start_time
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)

    accuracy = (passed / total) * 100 if total > 0 else 0
    print("=== Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"Total Runtime: {minutes}m {seconds}s")
    print("==================")


if __name__ == "__main__":
    run_tests()
