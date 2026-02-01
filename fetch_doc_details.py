import requests
import json

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZWNhOWM5ZmItNTQ0ZS00ZTkwLWFlMmItYTc3YzRlMTdjZTVkIiwib3JnX2lkIjoiY2IyYmE4NGMtMWJhOS00MDExLWIxYzMtNDBjYTk0OGIzZThlIiwiZW1haWwiOiJkZW1vQGxlZGdlcmx5LmFwcCIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3MDU2NTUzN30.Wm0Zow6yo5LXZcnHos3tMx2BFtKlFMbSILwK9-X9M-0"
document_id = "d95937c0-d90d-481e-adb3-e4594470baab"
url = f"http://localhost:8000/documents/{document_id}"
headers = {"Authorization": f"Bearer {token}"}

try:
    response = requests.get(url, headers=headers)
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
