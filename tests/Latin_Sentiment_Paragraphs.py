import requests
import json
import string
import time
import re
from typing import List, Dict

# Configuration for the Ollama server
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "LatinSentimentAnalysis:latest"
OLLAMA_TAGS_URL = OLLAMA_API_URL.replace("/api/generate", "/api/tags")
OLLAMA_PULL_URL = OLLAMA_API_URL.replace("/api/generate", "/api/pull")


# Load test cases from JSON file
def load_test_cases(
    file_path: str = "LatinParagraphsTestData.json",
) -> List[Dict[str, str]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON must be a list of dictionaries")
            for i, item in enumerate(data):
                if not isinstance(item, dict) or "paragraph" not in item:
                    raise ValueError(f"Invalid test case at index {i}: {item}")
            return data
    except Exception as e:
        print(f"Error loading test cases from {file_path}: {str(e)}")
        return []


def clean_sentiment(text: str) -> str:
    cleaned = text.strip().lower().rstrip(string.punctuation + string.whitespace)
    return cleaned.split()[0] if cleaned else ""


def parse_sentiment_detailed(raw_output: str) -> dict:
    match = re.search(r"SENTIMENT RESULTS:\s*(.+)", raw_output, re.IGNORECASE)
    if not match:
        return {
            "full_label": None,
            "base_sentiment": None,
            "intensity": None,
            "score": None,
        }

    full_label = match.group(1).strip()
    detail_match = re.match(
        r"(?P<intensity>EXTREMELY|VERY|MODERATELY)?\s*(?P<base>POSITIVE|NEGATIVE|NEUTRAL)\s*(\((?P<score>[+-]?\d+)\))?",
        full_label,
        re.IGNORECASE,
    )
    if detail_match:
        base = detail_match.group("base").upper()
        intensity = (
            detail_match.group("intensity").upper()
            if detail_match.group("intensity")
            else None
        )
        score = (
            int(detail_match.group("score")) if detail_match.group("score") else None
        )
        if score is None:
            score_match = re.search(r"Score:\s*([+-]?\d+)", raw_output, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else None
        return {
            "full_label": full_label,
            "base_sentiment": base,
            "intensity": intensity,
            "score": score,
        }
    return {
        "full_label": full_label,
        "base_sentiment": None,
        "intensity": None,
        "score": None,
    }


def preload_model() -> bool:
    print(f"Attempting to preload model {OLLAMA_MODEL}...")
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

    try:
        payload = {"name": OLLAMA_MODEL}
        response = requests.post(OLLAMA_PULL_URL, json=payload, timeout=120)
        response.raise_for_status()
        print(f"Model {OLLAMA_MODEL} pulled successfully.")
    except Exception as e:
        print(f"Failed to pull model {OLLAMA_MODEL}: {str(e)}")
        return False

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


def query_ollama(paragraph: str, retries: int = 2) -> tuple[str, str]:
    prompt = f"{paragraph}"
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": True}
    last_raw = ""
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                OLLAMA_API_URL, json=payload, stream=True, timeout=60
            )
            response.raise_for_status()

            full_response = ""
            sentiment_line = None
            start_time = time.time()
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    token = chunk.get("response", "")
                    full_response += token
                    lines = full_response.split("\n")
                    for l in lines:
                        if l.strip().startswith("SENTIMENT RESULTS:"):
                            if re.match(
                                r"SENTIMENT RESULTS:\s*(EXTREMELY|VERY|MODERATELY)?\s*(POSITIVE|NEGATIVE|NEUTRAL)(\s*\([+-]?\d+\))",
                                l,
                                re.IGNORECASE,
                            ):
                                sentiment_line = l.strip()
                                break
                    if sentiment_line:
                        cleaned = clean_sentiment(sentiment_line)
                        return cleaned, sentiment_line
                    if chunk.get("done", False) or (time.time() - start_time > 5):
                        break
                last_raw = full_response
            print(
                f"Empty or invalid response, retrying attempt {attempt + 1}/{retries + 1}"
            )
        except Exception as e:
            last_raw = f"Error: {str(e)}"
            print(
                f"Request failed, retrying attempt {attempt + 1}/{retries + 1}: {str(e)}"
            )
        if attempt < retries:
            time.sleep(2)
    return "error", last_raw


def run_tests(test_cases: List[Dict[str, str]] = None):
    if test_cases is None:
        test_cases = load_test_cases()
    total = len(test_cases)
    passed = 0
    failed = 0

    start_time = time.perf_counter()

    if not check_server():
        print("Aborting tests due to server or model issues.")
        return

    print("=== Latin Sentiment Analysis Test Suite for Paragraphs ===")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Total Test Cases: {total}")
    print(f"Ollama Server: {OLLAMA_API_URL}")
    print("-" * 80)

    for idx, item in enumerate(test_cases, start=1):
        try:
            paragraph = item["paragraph"]
            expected_full = item.get("expected_sentiment", "")
            expected_base = (
                expected_full.split()[1]
                if " " in expected_full
                else expected_full.lower()
            )
            expected_sign = (
                1 if "+" in expected_full else -1 if "-" in expected_full else 0
            )
            translation = item.get("translation", "")

            test_start = time.perf_counter()
            predicted, raw_response = query_ollama(paragraph, retries=2)
            test_time = time.perf_counter() - test_start

            time.sleep(2)

            parsed = parse_sentiment_detailed(raw_response)
            predicted_full = parsed["full_label"]
            predicted_base = parsed["base_sentiment"]
            predicted_score = parsed["score"]

            if predicted_full == expected_full:
                status = "PASSED"
                passed += 1
            elif (
                predicted_base == expected_base
                and predicted_score is not None
                and (
                    predicted_score > 0
                    if expected_sign > 0
                    else (
                        predicted_score < 0
                        if expected_sign < 0
                        else predicted_score == 0
                    )
                )
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
                note = f"Wrong base/direction or parsing failed (expected: {expected_base}, got: {predicted_base}, score: {predicted_score})"

            display_pred = predicted_full or "EXTRACT FAILED"
            display_exp = expected_full

            print(f"Test {idx}/{total}:")
            print(f"  Paragraph: {paragraph}")
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
        except Exception as e:
            print(f"Error processing test {idx}: {str(e)}")
            failed += 1
            print(f"Test {idx}/{total}:")
            print(f"  Status: FAILED")
            print(f"  Test Time: N/A")
            print("-" * 80)

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
    test_cases = load_test_cases()
    if test_cases:
        run_tests(test_cases)
    else:
        print("No test cases found in LatinParagraphsTestData.json")
