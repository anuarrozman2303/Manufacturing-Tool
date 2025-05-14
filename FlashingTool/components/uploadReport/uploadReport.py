# uploadReport.py
import requests
import logging

logger = logging.getLogger(__name__)

def post_report(api_url, data, headers=None):
    """
    Function to post data to a specified API endpoint.

    :param api_url: The URL of the API endpoint.
    :param data: The data to be posted to the API (typically in JSON format).
    :param headers: Optional headers to include in the request.
    :return: Response object from the API request.
    """
    try:
        response = requests.post(api_url, json=data, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        logger.info(f"Report successfully uploaded. Status code: {response.status_code}")
        return response
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")
        return None
