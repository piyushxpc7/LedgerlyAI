import requests
import time
import json

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZWNhOWM5ZmItNTQ0ZS00ZTkwLWFlMmItYTc3YzRlMTdjZTVkIiwib3JnX2lkIjoiY2IyYmE4NGMtMWJhOS00MDExLWIxYzMtNDBjYTk0OGIzZThlIiwiZW1haWwiOiJkZW1vQGxlZGdlcmx5LmFwcCIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3MDU2NTUzN30.Wm0Zow6yo5LXZcnHos3tMx2BFtKlFMbSILwK9-X9M-0"
document_id = "d95937c0-d90d-481e-adb3-e4594470baab"
headers = {"Authorization": f"Bearer {token}"}

# Trigger Ingestion
ingest_url = f"http://localhost:8000/documents/{document_id}/run-ingestion"
print(f"Triggering ingestion for {document_id}...")
try:
    resp = requests.post(ingest_url, headers=headers)
    print(f"Ingestion Trigger Status: {resp.status_code}")
    print(resp.text)
except Exception as e:
    print(f"Trigger Error: {e}")
    exit(1)

# Poll Status
status_url = f"http://localhost:8000/documents/{document_id}/status"
print("Polling status...")
for i in range(10):  # Poll for 20 seconds
    try:
        resp = requests.get(status_url, headers=headers)
        data = resp.json()
        status = data.get("status")
        print(f"Status: {status}")
        
        if status in ["processed", "completed", "failed"]:
            print("Final Status Reached")
            break
        
        time.sleep(2)
    except Exception as e:
        print(f"Poll Error: {e}")
        time.sleep(2)
