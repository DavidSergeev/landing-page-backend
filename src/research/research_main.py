import requests
from src.service_utils.logger import get_logger

logger = get_logger()


def http_request(url: str) -> str:
    """Perform a simple HTTP GET and return the response text."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def main() -> None:
    """Entry point for research scraping."""
    response = http_request("https://il.flightnetwork.com/rf/start")
    logger.info("Response length: %d chars", len(response))


if __name__ == "__main__":
    main()
