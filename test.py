import requests
import json

def fetch_crypto_data():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    response = requests.get(url)
    data = json.loads(response.text)
    print("Current Bitcoin price in USD:", data['bitcoin']['usd'])

if __name__ == "__main__":
    fetch_crypto_data()
