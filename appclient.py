from tgtg import TgtgClient, TgtgAPIError


class AppClient(TgtgClient):

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

    def refresh_token(self):
        return self.login()

    def get_item_texts(self, show_unavailable=False):
        for item in self.get_items():
            if (item.get("items_available") > 0) or show_unavailable:
                yield make_item_text(item)

    def get_new_items_texts(self):
        for item in self.get_new_items():
            yield make_item_text(item)

    def get_new_items(self):
        pass # TODO


def make_item_text(item):
    return "placeholder"
