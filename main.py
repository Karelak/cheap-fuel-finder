import time
import json
from dotenv import load_dotenv
import os
import requests


class API_Fetcher:
    def __init__(self, client_id, client_secret):
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.access_token: str = None
        self.refresh_token: str = None
        self.expires_in: int = None

    def fetch_token(self):
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = requests.post(
            url="https://www.fuel-finder.service.gov.uk/api/v1/oauth/generate_access_token",
            data=data,
        )
        response.raise_for_status()
        token_data = response.json()["data"]
        self.access_token = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]
        self.expires_in = token_data["expires_in"]
        return self.access_token, self.refresh_token, self.expires_in

    def regenerate_access_token(self):
        data = {
            "client_id": self.client_id,
            "refresh_token": self.refresh_token,
        }
        response = requests.post(
            url="https://www.fuel-finder.service.gov.uk/api/v1/oauth/regenerate_access_token",
            data=data,
        )
        response.raise_for_status()
        token_data = response.json()["data"]
        self.access_token = token_data["access_token"]
        self.expires_in = token_data["expires_in"]
        return self.access_token, self.expires_in

    def fetch_pfs_info(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        finished = False
        batch_number = 1
        data = []
        while not finished:
            try:
                response = requests.get(
                    url="https://www.fuel-finder.service.gov.uk/api/v1/pfs",
                    headers=headers,
                    params={"batch-number": batch_number},
                )
                response.raise_for_status()

            except requests.exceptions.HTTPError as e:
                match e.response.status_code:
                    case 401:
                        self.access_token, self.expires_in = (
                            self.regenerate_access_token()
                        )
                        headers["Authorization"] = f"Bearer {self.access_token}"
                    case 429:
                        print("Rate limit exceeded. Retrying in 60 seconds...")
                        time.sleep(60)
                    case 404:
                        print("No more batches to fetch.")
                        finished = True
                    case _:
                        raise

            else:
                print(f"Batch {batch_number} completed.")
                data.append(response.json())
                batch_number += 1
        return data


if __name__ == "__main__":
    load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    api_fetcher = API_Fetcher(client_id, client_secret)
    api_fetcher.fetch_token()
    with open("pfs_data.json", "w") as f:
        json.dump(api_fetcher.fetch_pfs_info(), f, indent=2)
