
import os
from openaq import OpenAQ

client = OpenAQ(api_key=os.environ["OPENAQ_API_KEY"])

stations = {
    "Pune": [2585, 5661, 60658],
    "Mumbai": [6927, 6956, 6959],
    "Nashik": [5592, 3409451, 3409453],
    "Nagpur": [5621, 3409464, 3409465],
}

try:
    for city, location_ids in stations.items():
        print(f"\n{'=' * 12} {city} {'=' * 12}")

        for location_id in location_ids:
            try:
                response = client.locations.sensors(location_id)
                sensors = response.results
                found = False

                for sensor in sensors:
                    parameter = getattr(sensor, "parameter", None)
                    parameter_name = (
                        getattr(parameter, "name", "") or ""
                    ).lower()

                    if (
                        getattr(parameter, "id", None) == 2
                        or "pm25" in parameter_name.replace(".", "")
                        or "pm2.5" in parameter_name
                    ):
                        found = True
                        print(
                            f"Location ID: {location_id} | "
                            f"Sensor ID: {sensor.id} | "
                            f"Name: {sensor.name}"
                        )
                        print(
                            f"First: {sensor.datetime_first} | "
                            f"Last: {sensor.datetime_last}"
                        )

                if not found:
                    print(
                        f"Location {location_id}: "
                        "No PM2.5 sensor identified"
                    )

            except Exception as error:
                print(
                    f"Location {location_id}: "
                    f"{type(error).__name__}: {error}"
                )

finally:
    client.close()
