from main import CheapestFuelStationFinder

if __name__ == "__main__":
    finder = CheapestFuelStationFinder(
        user_address="Address of the user",
        max_distance=99999999999,
        fuel_type="B7_Standard",
    )
    cheapest_station = finder.find_cheapest_station()
    print("Cheapest station found: ", cheapest_station)
