import requests
import json

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZWNhOWM5ZmItNTQ0ZS00ZTkwLWFlMmItYTc3YzRlMTdjZTVkIiwib3JnX2lkIjoiY2IyYmE4NGMtMWJhOS00MDExLWIxYzMtNDBjYTk0OGIzZThlIiwiZW1haWwiOiJkZW1vQGxlZGdlcmx5LmFwcCIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3MDU2NTUzN30.Wm0Zow6yo5LXZcnHos3tMx2BFtKlFMbSILwK9-X9M-0"
url = "http://localhost:8000/clients"
headers = {"Authorization": f"Bearer {token}"}

try:
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
