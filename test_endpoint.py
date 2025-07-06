import requests
import json

# API endpoint URL
url = "https://8jwpdmqgza.execute-api.ap-south-1.amazonaws.com/"

# Sample transaction data (29 features V1-V28 + Amount)
test_data = {
    "V1": -1.359807134,
    "V2": -0.072781173,
    "V3": 2.536346738,
    "V4": 1.378155224,
    "V5": -0.338320770,
    "V6": 0.462387778,
    "V7": 0.239598554,
    "V8": 0.098697901,
    "V9": 0.363786969,
    "V10": 0.090794172,
    "V11": -0.551599533,
    "V12": -0.617800856,
    "V13": -0.991389847,
    "V14": -0.311169354,
    "V15": 1.468176972,
    "V16": -0.470400525,
    "V17": 0.207971242,
    "V18": 0.025791653,
    "V19": 0.403992960,
    "V20": 0.251412098,
    "V21": -0.018306778,
    "V22": 0.277837576,
    "V23": -0.110473910,
    "V24": 0.066928075,
    "V25": 0.128539358,
    "V26": -0.189114844,
    "V27": 0.133558377,
    "V28": -0.021053053,
    "Amount": 149.62
}

# Make POST request
response = requests.post(url, json=test_data)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")