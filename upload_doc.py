import requests

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZWNhOWM5ZmItNTQ0ZS00ZTkwLWFlMmItYTc3YzRlMTdjZTVkIiwib3JnX2lkIjoiY2IyYmE4NGMtMWJhOS00MDExLWIxYzMtNDBjYTk0OGIzZThlIiwiZW1haWwiOiJkZW1vQGxlZGdlcmx5LmFwcCIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3MDU2NTUzN30.Wm0Zow6yo5LXZcnHos3tMx2BFtKlFMbSILwK9-X9M-0"
client_id = "338ebf9b-fedb-4fe6-a132-5985269765cc"
url = f"http://localhost:8000/documents/clients/{client_id}/documents"
headers = {"Authorization": f"Bearer {token}"}

files = {
    'file': ('test_statement.csv', open('/Users/Work/AICA/test_statement.csv', 'rb'), 'text/csv'),
    'doc_type': (None, 'bank')
}

try:
    response = requests.post(url, headers=headers, files=files)
    print(f"Status: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
