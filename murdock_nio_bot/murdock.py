import asyncio
import datetime
import json
import logging
import random

import requests

from .chat_functions import send_text_to_room

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


def commit_markdown_link(commit):
    """
    Generates a markdown link to GitHub from a commit hash
    """
    return f"[{commit[:10]}](https://github.com/RIOT-OS/RIOT/commit/{commit})"


def generate_message(greeting, results):
    """
    Generates a message from nightlies results
    """
    msg = f"{greeting} Here is my morning report for the nightlies:\n\n"

    for branch, result in [(b, r) for b, r in results if r["result"] == "passed"]:
        commit_link = commit_markdown_link(result["commit"])
        msg += (
            f'- [`{branch}` passed]({result["url"]}) on {commit_link} '
            f"after having errored last time\n"
        )
    for branch, result in [(b, r) for b, r in results if r["result"] == "errored"]:
        commit_link = commit_markdown_link(result["commit"])
        msg += f'- [`{branch}` errored]({result["url"]}) on {commit_link}'
    return msg


async def report_last_nightlies(client, branches):
    """
    Reports last nightlies to all rooms the bot is in
    """
    results = [
        (branch, Nightlies(branch).check_if_last_errored_or_changed_to_passed())
        for branch in branches
    ]
    if all(result is None for _, result in results):
        return
    msg = generate_message(
        random.choice(("Hello", "Greetings", "Good Morning"))
        + random.choice((" RIOTers!", " fellow humans!", "!")),
        results,
    )
    tasks = []
    for room_id in client.rooms:
        tasks.append(
            asyncio.create_task(
                send_text_to_room(client, room_id, msg, markdown_convert=True)
            )
        )
    await asyncio.wait(tasks)
