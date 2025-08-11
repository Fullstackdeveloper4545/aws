import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class TrackageClient:
    def __init__(self, base_url, username, password, max_retries=3, backoff_factor=1):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None

        # Create a requests session and configure retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],  # POST included for idempotent endpoints
            backoff_factor=backoff_factor
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def authenticate(self):
        """Authenticate and store a token for future requests."""
        auth_url = f"{self.base_url}/auth/login"
        payload = {"username": self.username, "password": self.password}
        response = self.session.post(auth_url, json=payload, timeout=10)
        response.raise_for_status()
        self.token = response.json().get('access_token')
        if not self.token:
            raise Exception("Authentication failed; no token returned.")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def post_payload(self, endpoint, payload):
        """POST a payload to the backend with authentication, retries, and response handling."""
        if not self.token:
            self.authenticate()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            try:
                return response.json()  # Return parsed JSON if response is JSON
            except ValueError:
                return response.text     # Return raw text if not JSON
        except requests.RequestException as e:
            # Handle and log errors as needed
            print(f"POST failed: {e}")
            raise

# Example usage:
if __name__ == "__main__":
    client = TrackageClient("https://trackage-api.example.com", "username", "password", max_retries=5, backoff_factor=2)
    data = {"shipment_id": "12345", "status": "delivered"}
    result = client.post_payload("api/track/update", data)
    print(result)
