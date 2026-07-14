import requests

url = "https://tools.dongvanfb.net/api/graph_messages"
payload = {
    "email": "jaidemortimeracacia1606@hotmail.com",
    "refresh_token": "M.C515_BAY.0.U.MsaArtifacts.-CjE9WjC9Ib6J2JeoSIqG48E7qIpi0OYBXXHz6mdfYuwUNhQx7Ovg9qZAz750Yi11ZG3jMEbXblxMQp3fPWt*v1egpBJwlbIrM!TtrL4dUPeIzVtZ1QiYwkS06U2uY6x!*uJbNzrAB7cspxCwOheAof70rTbfvezuqqoJiJGryHF98ylkZx6GSID0PjZXihM9TnP8aAyETTSsQPbV02nFSpCBWVHwZ8CupRJDzANVDlFPy65Ph*adeFAWPwIn16QttdfgLz5xLlxXC6PkUTBBf1sjVUl8nH*EkpJi6tnHM3FMLetkLhFFguRGGnjaHGn0IXJ08Q!RlBPmnEjQWSIFViAJQDNOI0aXtmqxaU2k*t9BhYRwVWEMOow1rCXFDvyMSwCj8dAY4P7HUU!0jwZrFiA$",
    "client_id": "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
}
print("Checking messages...")
res = requests.post(url, json=payload)
print(res.status_code, res.text)

url2 = "https://tools.dongvanfb.net/api/graph_code"
payload2 = payload.copy()
payload2["type"] = "amazon"
print("\nChecking code...")
res2 = requests.post(url2, json=payload2)
print(res2.status_code, res2.text)
