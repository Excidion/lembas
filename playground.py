from tgtg import TgtgClient
from dotenv import load_dotenv
import os

load_dotenv()

client = TgtgClient(
    access_token = os.getenv("access_token"),
    refresh_token = os.getenv("refresh_token"), 
    user_id = os.getenv("user_id"),
)

items = client.get_items()

for item in items:
    store_name = item["store"]["store_name"]
    store_adress = item["store"]["store_location"]["address"]["address_line"]
    item_name = item["item"]["name"]
    item_price = item["item"]["price_including_taxes"]["minor_units"] / (10**item["item"]["price_including_taxes"]["decimals"])
    items_available = item["items_available"]
    pickup_start = item["pickup_interval"]["start"]
    pickup_end = item["pickup_interval"]["end"]

    if items_available > 0:
        print(f"{store_name} has {items_available} {item_name} avaiable for {item_price}€ each.")
        print(f"You can pick it up at {store_adress} from {pickup_start} to {pickup_end}")