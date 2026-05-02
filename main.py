import requests
from dotenv import load_dotenv
import os

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
base_url = "https://www.fuel-finder.service.gov.uk/api/v1/"


def get_access_token(client_id: str, client_secret: str) -> dict:
    if not client_id or not client_secret:
        raise ValueError("CLIENT_ID and CLIENT_SECRET must be set in the environment")

    response = requests.post(
        url=f"{base_url}oauth/generate_access_token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(client_id: str, refresh_token: str) -> dict:
    if not client_id or not refresh_token:
        raise ValueError("CLIENT_ID and REFRESH_TOKEN must be set in the environment")

    response = requests.post(
        url=f"{base_url}oauth/regenerate_access_token",
        json={
            "client_id": client_id,
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
