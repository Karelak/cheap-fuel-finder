import time
from dotenv import load_dotenv
import os
import simdjson as json
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from datetime import datetime


class CheapestFuelStationFinder:
    def __init__(
        self, user_address="10 Downing Street", max_distance=5, fuel_type="E5"
    ):
        load_dotenv()
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        tokens = self.generate_access_token()
        self.access_token = tokens[0]
        self.refresh_token = tokens[1]
        self.user_address = user_address
        self.max_distance = max_distance
        self.fuel_type = fuel_type.upper()

    def generate_access_token(self):
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

        return self.access_token, self.refresh_token

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
        token_data = response.json()
        self.access_token = token_data["access_token"]

        return self.access_token

    def fetch_pfs_info(self):
        if (
            os.path.exists("data/stations.json")
            and os.path.getmtime("data/stations.json") > time.time() - 1 * 3600
        ):
            print("Using cached station data.")
            with open("data/stations.json", "r") as f:
                return json.loads(f.read())
        headers = {"Authorization": f"Bearer {self.access_token}"}
        finished = False
        batch_number = 1
        stations = []
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
                        self.access_token = self.regenerate_access_token()
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
                stations.extend(response.json())
                batch_number += 1

        if not os.path.exists("data"):
            os.makedirs("data")
        with open("data/stations.json", "w") as f:
            json.dump(stations, f, indent=4)

        return stations

    def fetch_pfs_prices(self):
        if (
            os.path.exists("data/prices.json")
            and os.path.getmtime("data/prices.json") > time.time() - 15 * 60
        ):
            print("Using cached price data.")
            with open("data/prices.json", "r") as f:
                return json.loads(f.read())
        headers = {"Authorization": f"Bearer {self.access_token}"}
        finished = False
        batch_number = 1
        prices = []
        while not finished:
            try:
                response = requests.get(
                    url="https://www.fuel-finder.service.gov.uk/api/v1/pfs/fuel-prices",
                    headers=headers,
                    params={"batch-number": batch_number},
                )
                response.raise_for_status()

            except requests.exceptions.HTTPError as e:
                match e.response.status_code:
                    case 401:
                        self.access_token = self.regenerate_access_token()
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
                prices.extend(response.json())
                batch_number += 1

        if not os.path.exists("data"):
            os.makedirs("data")
        with open("data/prices.json", "w") as f:
            json.dump(prices, f, indent=4)

        return prices

    def get_users_closest_stations(self):
        stations = self.fetch_pfs_info()
        user_coordinates = Nominatim(user_agent="cheap-fuel-finder").geocode(
            self.user_address
        )
        nearby_stations = []
        for station in stations:
            station_coordinates = (
                station["location"]["latitude"],
                station["location"]["longitude"],
            )
            distance = geodesic(
                (user_coordinates.latitude, user_coordinates.longitude),
                station_coordinates,
            ).kilometers
            if distance <= self.max_distance:
                nearby_stations.append(station)

        return nearby_stations

    def find_cheapest_station(self):
        nearby_stations = self.get_users_closest_stations()
        prices = self.fetch_pfs_prices()
        cheapest_station = None
        cheapest_price = float("inf")

        for station in nearby_stations:
            for price_entry in prices:
                if price_entry["node_id"] == station["node_id"]:
                    for fuel in price_entry["fuel_prices"]:
                        if (
                            fuel["fuel_type"] == self.fuel_type
                            and fuel["price"] < cheapest_price
                            and fuel["price"] > 0
                            and fuel["price"] is not None
                            and fuel["price"] != 1
                            and datetime.fromisoformat(
                                fuel["price_change_effective_timestamp"]
                            ).timestamp()
                            > time.time() - 24 * 3600 * 7
                        ):
                            cheapest_price = fuel["price"]
                            cheapest_station = {
                                "node_id": price_entry["node_id"],
                                "trading_name": price_entry["trading_name"],
                                "price": fuel["price"],
                            }

                    break  # Move to next station once we find the matching node_id

        return cheapest_station
