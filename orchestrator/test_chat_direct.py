import urllib.request
import json
import time

url = "http://127.0.0.1:8888/api/chat"

test_prompts = [
    {"message": "whats wrong with notification service ?", "history": []},
    {"message": "fix notification service", "history": [{"role": "model", "content": "notification-service ImagePullBackOff nginx:v999-broken-tag"}]},
    {"message": "whats wrong with order service ?", "history": []},
    {"message": "fix order service", "history": [{"role": "model", "content": "order-service REDIS_HOST missing"}]}
]

for item in test_prompts:
    t0 = time.time()
    payload = {
        "message": item["message"],
        "namespace": "production",
        "history": item["history"]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res = json.loads(response.read().decode("utf-8"))
            elapsed = round((time.time() - t0) * 1000, 1)
            print(f"[SUCCESS] Prompt: '{item['message']}' ({elapsed}ms)")
            if res.get("requires_approval"):
                print(f" -> TRIGGERED HITL APPROVAL: Tool='{res.get('tool_name')}', Args={res.get('args')}")
            else:
                snippet = str(res.get("response", ""))[:120].replace('\n', ' ')
                print(f" -> RESPONSE: {snippet}...")
    except Exception as e:
        print(f"[FAILED] {item['message']}: {e}")
