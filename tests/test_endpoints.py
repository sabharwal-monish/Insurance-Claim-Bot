# tests/test_endpoints.py

import requests

BASE_URL = "http://localhost:8000"

def test_root():
    response = requests.get(BASE_URL + "/")
    assert response.status_code == 200
    print("✅ Root endpoint works!")

def test_webhook():
    payload = {
        "message": "I want to file a claim",
    }
    response = requests.post(BASE_URL + "/claims/webhook", json=payload)
    assert response.status_code == 200
    print("✅ Webhook endpoint works!")

# Run tests manually
if __name__ == "__main__":
    test_root()
    test_webhook()
