from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("GROQAPIKEY"),
    base_url="https://api.groq.com/openai/v1",
)



def webTranslation(latinText):
    response = client.responses.create(
        input=f"Latin to English translation for: {latinText}",
        model="openai/gpt-oss-20b",
    )
    return response.output_text
