import datetime
import json
import logging

import requests

logger = logging.getLogger(__name__)

NIGHTLIES_URL = "https://ci.riot-os.org/RIOT-OS/RIOT/{branch}/nightlies.json"
RESULT_URL = "https://ci.riot-os.org/RIOT-OS/RIOT/{branch}/{commit}/output.html"
DEFAULT_BRANCH = "master"


class Nightlies:
    """
    Class to represent Murdock nightlies

    :param branch: the Git branch for which the nightlies are.
    """

    def __init__(self, branch=DEFAULT_BRANCH):
        self.branch = branch

    def get_nightlies(self):
        """
        Get current list of nightlies
        """
        nightlies_url = NIGHTLIES_URL.format(branch=self.branch)
        request = requests.get(nightlies_url)
        if request.status_code != 200:
            logger.error(
                "Unable to GET %s\n%d %s",
                nightlies_url,
                request.status_code,
                request.text,
            )
            return []
        try:
            return request.json()
        except json.JSONDecodeError as exc:
            logger.error("Unable to decode: %s\n%s", exc, request.text)
            return []

    def check_if_last_errored_or_changed_to_passed(self):
        """
        Returns the latest nightly result of self.branch when it errored or
        changed from errored to passed compared to the nightly before. Returns
        ``None`` if both conditions do not apply
        """
        results = self.get_nightlies()
        if len(results) > 0:
            if results[0]["result"] == "errored" or (
                len(results) > 1
                and results[1]["result"] == "errored"
                and results[0]["result"] == "passed"
            ):
                result = results[0]
                result["since"] = datetime.datetime.utcfromtimestamp(result["since"])
                result["url"] = RESULT_URL.format(
                    commit=result["commit"], branch=self.branch
                )
                return result
        return None
