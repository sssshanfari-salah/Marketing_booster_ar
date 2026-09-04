import json
from datetime import datetime
from pathlib import Path
from typing import List


class Client:
    def __init__(self, name: str, contact: str, business: str, email: str = "", shop_number: str = "", reviews=None):
        self.name = name
        self.contact = contact
        self.business = business
        self.email = email
        self.shop_number = shop_number
        self.reviews = []

        if reviews is not None:
            for review in reviews:
                if isinstance(review, dict):
                    self.reviews.append({
                        "date": review.get("date", ""),
                        "review": review.get("review", ""),
                    })
                elif isinstance(review, str):
                    self.reviews.append({"date": "", "review": review})

    def to_dict(self):
        return {
            "name": self.name,
            "contact": self.contact,
            "business": self.business,
            "email": self.email,
            "shop_number": self.shop_number,
            "reviews": list(self.reviews),
        }

    @classmethod
    def from_dict(cls, data):
        reviews = data.get("reviews", [])
        if not isinstance(reviews, list):
            reviews = []
        return cls(
            data.get("name", ""),
            data.get("contact", ""),
            data.get("business", ""),
            data.get("email", ""),
            shop_number=str(data.get("shop_number", "")),
            reviews=reviews,
        )

    def __repr__(self):
        return f"Client name: {self.name}\nContact: {self.contact}\nType of business: {self.business}\nEmail: {self.email}\nReviews: {len(self.reviews)}"


class ClientManager:
    def __init__(self, file_path=None):
        if file_path is None:
            file_path = Path(__file__).resolve().parent.parent / "clients.json"
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]", encoding="utf-8")
        self.clients = []
        self.load_clients()

    def add_client(self, name: str, contact: str, business: str, email: str = ""):
        client = Client(name, contact, business, email)
        self.clients.append(client)
        self.save_clients()

    def delete_client(self, name: str):
        if not name or not isinstance(name, str):
            return False

        target_name = name.strip()
        if not target_name:
            return False

        before = len(self.clients)
        self.clients = [client for client in self.clients if client.name.lower() != target_name.lower()]

        if len(self.clients) == before:
            return False

        self.save_clients()
        return True

    def add_review(self, name: str, review_text: str):
        if not name or not isinstance(name, str):
            return False

        target_name = name.strip()
        review = str(review_text or "").strip()
        if not target_name or not review:
            return False

        client = next((item for item in self.clients if item.name.lower() == target_name.lower()), None)
        if client is None:
            return False

        client.reviews.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "review": review,
        })
        self.save_clients()
        return True

    def get_all_reviews(self):
        reviews = []
        for client in self.clients:
            for review in client.reviews:
                reviews.append({
                    "client_name": client.name,
                    "contact": client.contact,
                    "business": client.business,
                    "email": client.email,
                    "date": review.get("date", ""),
                    "review": review.get("review", ""),
                })

        reviews.sort(key=lambda item: (item.get("date", "") or "", item.get("client_name", "").lower()))
        return reviews

    def list_clients(self):
        if not self.clients:
            return "No clients found."

        result = []
        for client in self.clients:
            email_info = f" | {client.email}" if client.email else ""
            result.append(f"{client.name} | {client.contact} | {client.business}{email_info}")
        return "\n".join(result)

    def search_clients(self, keyword: str):
        keyword_lower = keyword.lower()
        return [
            client
            for client in self.clients
            if keyword_lower in client.name.lower()
            or keyword_lower in client.contact.lower()
            or keyword_lower in client.business.lower()
            or keyword_lower in client.email.lower()
        ]

    def save_clients(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [client.to_dict() for client in self.clients]
        self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_clients(self):
        if not self.file_path.exists():
            self.clients = []
            return

        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            self.clients = [Client.from_dict(item) for item in data]
        except (json.JSONDecodeError, TypeError, ValueError):
            self.clients = []

    def json2txt(self):
        with self.file_path.open("r", encoding="utf-8") as infile:
            data = json.load(infile)

        output_path = Path(r"docs/clients_data.txt")
        with output_path.open("w", encoding="utf-8") as outfile:
            outfile.write(json.dumps(data, indent=2))