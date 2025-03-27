import requests
import os
from dotenv import load_dotenv

load_dotenv()

V2X_API_KEY = os.getenv("V2X_API_KEY")

def get_signal_phase(intersection_id: str, page=1, rows=20):
    url = "http://t-data.seoul.go.kr/apig/apiman-gateway/tapi/v2xSignalPhaseTimingInformation/1.0"
    params = {
        "apiKey": V2X_API_KEY,
        "pageNo": page,
        "numOfRows": rows
    }
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "intersectionId": intersection_id
    }

    try:
        response = requests.post(url, params=params, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"신호 API 실패: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}
