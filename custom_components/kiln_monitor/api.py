import logging

_LOGGER = logging.getLogger(__name__)


class KilnAPI:
    def __init__(self, session, email, password):
        self.session = session
        self.email = email
        self.password = password
        self.token = None

    async def authenticate(self):
        url = "https://bartinst-user-service-prod.herokuapp.com/login"

        payload = {
            "email": self.email,
            "password": self.password
        }

        async with self.session.post(url, json=payload) as resp:
            data = await resp.json()
            self.token = data["authentication_token"]

    def headers(self):
        return {
            "auth-token": f"binst-cookie={self.token}",
            "email": self.email,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "kaid-version": "kaid-plus",
            "x-app-name-token": "kiln-aid",
        }

    async def fetch_status(self, external_id):
        url = "https://kiln.bartinst.com/kilnaid-data/status"

        payload = {"externalIds": external_id}

        async with self.session.post(url, headers=self.headers(), json=payload) as resp:
            data = await resp.json()

        return data[0]

    async def fetch_summary(self, external_id):
        url = "https://kiln.bartinst.com/kilns/data"

        payload = {"externalIds": [external_id]}

        async with self.session.post(url, headers=self.headers(), json=payload) as resp:
            data = await resp.json()

        return data[0]

    async def fetch_view(self, serial_number):
        url = "https://kiln.bartinst.com/kilns/view"

        payload = {"ids": [serial_number]}

        async with self.session.post(url, headers=self.headers(), json=payload) as resp:
            data = await resp.json()

        return data["kilns"][0]