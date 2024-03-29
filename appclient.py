from tgtg import TgtgClient, TgtgAPIError
from datetime import datetime
from pytz import timezone as tz

class AppClient(TgtgClient):

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory = dict()

    @property
    def registration_email(self):
        try:
            return self._registration_email
        except AttributeError:
            return None

    @registration_email.setter
    def registration_email(self, email):
        assert self.registration_email is None, "Property already set."
        self._registration_email = email

    @registration_email.deleter
    def registration_email(self):
        assert self.registration_email is not None, "Property not set. Nothing to delete."
        del self._registration_email

    def get_scheduled_items_times(self):
        for item in self.get_scheduled_items():
            next_sale = item.get("next_sales_window_purchase_start")
            timezone = item.get("store").get("store_time_zone")
            next_sale = datetime.strptime(next_sale, "%Y-%m-%dT%H:%M:%S%z").astimezone(tz(timezone))
            yield next_sale

    def get_scheduled_items(self):
        for item in self.get_items():
            if item.get("items_available") > 0:
                continue # don't consider available ones
            # fetching with the get_item method returns more datapoints - one of which we need 
            item = self.get_item(item.get("item").get("item_id"))
            next_sale = item.get("next_sales_window_purchase_start")
            if next_sale is not None: # only use ones that have a scheduled date
                yield item 
            
    def get_item_texts(self, show_unavailable=False):
        for item in self.get_items():
            if (item.get("items_available") > 0) or show_unavailable:
                yield make_item_text(item)

    def get_new_item_texts(self):
        for item in self.get_new_items():
            yield make_item_text(item)

    def get_new_items(self):
        for item in self.get_items():
            item_id = item.get("item").get("item_id")
            items_available = item.get("items_available")
            items_available_before = self.memory.get(item_id, 0)
            self.memory[item_id] = items_available
            if items_available > items_available_before:
                yield item


def make_item_text(item):
    items_available = item["items_available"]
    store_name = item["store"]["store_name"]
    store_address = item["store"]["store_location"]["address"]["address_line"]
    item_name = item["item"]["name"]
    item_category = item["item"]["item_category"]
    price = item["item"]["price_including_taxes"]
    currency = price["code"]
    item_price = price["minor_units"] / (10**price["decimals"])
    timezone = item["store"]["store_time_zone"]
    pickup_start = datetime.strptime(item["pickup_interval"]["start"], "%Y-%m-%dT%H:%M:%S%z").astimezone(tz(timezone))
    pickup_end = datetime.strptime(item["pickup_interval"]["end"], "%Y-%m-%dT%H:%M:%S%z").astimezone(tz(timezone))
    pickup_today = datetime.today() == pickup_start.date()
    on = "" if pickup_today else f"on {pickup_start.date()} "
    msg0 = f"<b>{store_name}</b> has {items_available} {item_name or item_category} available for {item_price:.2f} {currency} each."
    msg1 = f"You can pick it up from {pickup_start.time().strftime('%H:%M')} to {pickup_end.time().strftime('%H:%M')} {on}at {store_address}."
    item_id = item["item"]["item_id"]
    link = f'<a href="https://share.toogoodtogo.com/item/{item_id}/">Grab it!</a>'
    return f"{msg0}\n{msg1}\n{link}"
