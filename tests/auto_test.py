import requests
import time


def run_tests(base_url="http://localhost:8000", retries=3):
    """
    Run simple health checks on the backend API and return True if successful.
    """
    for attempt in range(1, retries + 1):
        try:
            # wait a few seconds for the backend to start
            time.sleep(3)
            docs_response = requests.get(f"{base_url}/docs", timeout=5)
            openapi_response = requests.get(f"{base_url}/openapi.json", timeout=5)
            if docs_response.status_code == 200 and openapi_response.status_code == 200:
                print("Tests passed: Backend is running successfully!")
                return True
            else:
                print(
                    f"Attempt {attempt}: Unexpected status codes "
                    f"/docs={docs_response.status_code}, /openapi.json={openapi_response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}: Error connecting to backend - {e}")

    # if we reach here, tests failed
    return False
