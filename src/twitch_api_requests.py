from requests import get, post
from typing import Dict, List

def fetch_entitlements(token: str) -> List[Dict]:
    headers = {
        "x-auth-twitch": token,
        "Accept-Encoding": "gzip",
        "X-Amz-Target": "com.amazonaws.gearbox.softwaredistribution.service.model.SoftwareDistributionService.GetEntitlements",
        "Content-Encoding": "amz-1.0",
        "Content-Type": "application/json; charset=utf-8"
    }
    url = "https://sds.amazon.com/"

    r = post(url, headers=headers, json={ "clientId": "Fuel", "syncPoint": None })
    data = r.json()

    return data['entitlements'] if 'entitlements' in data else []


def validate_token(token: str) -> bool:
    headers = { "Authorization": f"OAuth {token}" }
    url = "https://id.twitch.tv/oauth2/validate"

    r = get(url, headers=headers)

    return r.status_code == 200
