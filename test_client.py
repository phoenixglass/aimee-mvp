import requests
response = requests.post(
    "http://localhost:5000/classify",
    json={"text": "Need 3 bottles of Merlot for Acme Restaurant"}
)
print(response.json())