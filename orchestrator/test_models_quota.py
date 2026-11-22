import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

candidate_models = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash"
]

print("[TEST] Testing candidate models for quota and speed:")
for m in candidate_models:
    try:
        res = client.models.generate_content(
            model=m,
            contents="Say 'OK'"
        )
        txt = res.text.strip().replace('\n', ' ') if res.text else "EMPTY"
        print(f" [PASS] {m}: SUCCESS ({txt})")
    except Exception as e:
        print(f" [FAIL] {m}: FAILED ({str(e)[:100]})")
