
import os
from openaq import OpenAQ

with OpenAQ(api_key=os.environ["OPENAQ_API_KEY"]) as client:
    response = client.measurements.list(
        sensors_id=12236449,
        data="days",
        date_from="2025-02-19",
        date_to="2025-02-25",
        limit=10,
    )

    print("Number of records:", len(response.results))

    for record in response.results[:3]:
        print(record)
