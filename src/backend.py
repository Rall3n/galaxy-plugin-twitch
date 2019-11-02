# import logging
import asyncio
from typing import Dict, List
from galaxy.http import create_client_session#, handle_exception

def sync_exec(coroutine):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine)

class TwitchBackendClient:
    VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
    ENTITLEMENTS_URL = "https://sds.amazon.com/"

    def __init__(self):
        self._session = create_client_session()

    async def validate_token(self, token) -> bool:
        headers = { "Authorization": f"OAuth {token}" }

        response = await self._session.request('GET', self.VALIDATE_URL, headers=headers)

        return response.status == 200

    async def fetch_entitlements(self, token) -> List[Dict]:
        headers = {
            "x-auth-twitch": token,
            "Accept-Encoding": "gzip",
            "X-Amz-Target": "com.amazonaws.gearbox.softwaredistribution.service.model.SoftwareDistributionService.GetEntitlements",
            "Content-Encoding": "amz-1.0",
            "Content-Type": "application/json; charset=utf-8"
        }

        json = { "clientId": "Fuel", "syncPoint": None }

        response = await self._session.request('POST', self.ENTITLEMENTS_URL, headers=headers, json=json)
        data = await response.json()

        return data['entitlements'] if 'entitlements' in data else []

    async def close(self) -> None:
        await self._session.close()