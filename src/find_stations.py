
import os
from openaq import OpenAQ

client = OpenAQ(api_key=os.environ["OPENAQ_API_KEY"])

cities = ["Pune", "Mumbai", "Nashik", "Nagpur"]

try:
    for city in cities:
        print(f"\n{'=' * 15} {city} {'=' * 15}")

        response = client.locations.list(
            limit=1000,
            page=1,
            parameters_id=2,
            iso="IN",
        )

        matches = [
            loc for loc in response.results
            if loc.name and city.lower() in loc.name.lower()
        ]

        if matches:
            for loc in matches:
                print(f"ID: {loc.id} | Name: {loc.name}")
                print(f"   Timezone: {loc.timezone}")
        else:
            print("No station name matched on this page.")
            print("This does not mean the city has no data.")

finally:
    client.close()
