import requests

class RailincClient:
    def __init__(self, username, password, api_base_url):
        self.username = username
        self.password = password
        self.api_base_url = api_base_url.rstrip('/')
        self.token = None
        self.session = requests.Session()  # Use a session for connection pooling

    def authenticate(self):
        """
        Authenticate with the Railinc API, store the bearer token for future requests.
        Adapt the payload and method to your specific API's requirements.
        """
        auth_url = f"{self.api_base_url}/auth/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        response = self.session.post(auth_url, json=payload)
        if response.status_code == 200:
            # Assuming token is in the 'access_token' field in JSON response
            self.token = response.json().get('access_token')
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            return True
        else:
            raise Exception(f"Authentication failed: {response.status_code} {response.text}")

    def get_fleet(self, yard_abbr):
        """
        Get fleet information for a specific yard.
        """
        if not self.token:
            self.authenticate()
        url = f"{self.api_base_url}/fleet/{yard_abbr}"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch fleet: {response.status_code} {response.text}")

    def get_equipment_details(self, equipment_id):
        """
        Get details of a piece of equipment.
        """
        if not self.token:
            self.authenticate()
        url = f"{self.api_base_url}/equipment/{equipment_id}"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch equipment details: {response.status_code} {response.text}")

    def get_movement_data(self, equipment_id):
        """
        Get movement data for a specific piece of equipment.
        """
        if not self.token:
            self.authenticate()
        url = f"{self.api_base_url}/equipment/{equipment_id}/movements"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch movement data: {response.status_code} {response.text}")

# Example usage:
if __name__ == "__main__":
    client = RailincClient("user", "pass", "https://railinc-api.example.com")
    client.authenticate()
    fleet = client.get_fleet("CHI")
    details = client.get_equipment_details("ABC123")
    movements = client.get_movement_data("ABC123")

    print(fleet)
    print(details)
    print(movements)
