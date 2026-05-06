import time
import json
from dotenv import load_dotenv
import os
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic as geodesic


class APIFetcher:
    def __init__(self, client_id, client_secret):
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.access_token: str = ""
        self.refresh_token: str = ""
        self.expires_in: int = -1

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
                for station in response.json():
                    data.append(station)
                batch_number += 1
        return data


class PersonalisedOptions:
    def __init__(self, user_address: str, max_distance: int, fuel_type: str):
        self.user_address: str = user_address
        self.user_coordinates: tuple[float, float] = self.get_user_coordinates()
        self.max_distance: int = max_distance
        self.fuel_type: str = fuel_type
        self.closest_stations: list[dict] = []
        self.cheapest_station: dict = {}

    def get_user_coordinates(self):
        geolocator = Nominatim(user_agent="best_fuel_station_finder")
        location = geolocator.geocode(self.user_address)
        self.user_coordinates = (location.latitude, location.longitude)
        return self.user_coordinates

    def search_closest_stations(self, stations):
        closest_stations = []
        for station in stations:
            station_coordinates = (
                station["location"]["latitude"],
                station["location"]["longitude"],
            )
            distance = geodesic(self.user_coordinates, station_coordinates).kilometers
            if distance <= self.max_distance:
                closest_stations.append(station)
        self.closest_stations = closest_stations
        return self.closest_stations

    def get_cheapest_fuel_price(self):
        cheapest_station = {}
        for station in self.closest_stations:
            fuel_types: list[str] = station["fuel_types"]
        # TODO: #5 setup the other api endpoint that has the fuel prices and merge it with the station data to get the fuel prices for each station
        self.cheapest_station = cheapest_station
        return self.cheapest_station


if __name__ == "__main__":
    load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    api_fetcher = APIFetcher(client_id, client_secret)
    api_fetcher.fetch_token()
    if not os.path.exists("pfs_data.json"):
        stations = api_fetcher.fetch_pfs_info()
    else:
        with open("pfs_data.json", "r") as f:
            stations = json.load(f)

    personalised_options = PersonalisedOptions("10 Downing Street, London, UK", 2, "E5")
    closest_stations = personalised_options.search_closest_stations(stations)
    cheapest_station = personalised_options.get_cheapest_fuel_price()
    with open("final.json", "w") as f:
        json.dump(cheapest_station, f, indent=4)
    # TODO: #1 setup the final output to show closest instead of just json
    # TODO: #2 add a function to update the pfs data every 24 hours or so to keep the data fresh
    # TODO: #3 setup the messager function to user via pushover or smth so that they can get input + output via that instead of the console
    # TODO: #4 cleanup
