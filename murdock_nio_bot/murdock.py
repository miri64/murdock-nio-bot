import asyncio
import datetime
import json
import logging
import random

import requests

from .chat_functions import send_text_to_room

logger = logging.getLogger(__name__)

DEFAULT_BRANCH = "master"


class Nightlies:
    """
    Class to represent Murdock nightlies

    :param branch: the Git branch for which the nightlies are.
    """

    def __init__(self, config, branch=DEFAULT_BRANCH):
        self.branch = branch
        self.config = config

    def get_nightlies(self):
        """
        Get current list of nightlies
        """
        nightlies_url = self.config.nightlies_url.format(branch=self.branch)
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
                result["url"] = self.config.result_url.format(
                    commit=result["commit"], branch=self.branch
                )
                return result
        return None


def commit_markdown_link(config, commit):
    """
    Generates a markdown link to GitHub from a commit hash
    """
    commit_url = config.commit_url.format(commit=commit)
    return f"[{commit[:10]}]({commit_url})"


def generate_message(config, greeting, results):
    """
    Generates a message from nightlies results
    """
    msg = f"{greeting} Here is my morning report for the nightlies:\n\n"

    for branch, result in [(b, r) for b, r in results if r["result"] == "passed"]:
        commit_link = commit_markdown_link(config, result["commit"])
        msg += (
            f'- [`{branch}` passed]({result["url"]}) on {commit_link} '
            f"after having errored last time\n"
        )
    for branch, result in [(b, r) for b, r in results if r["result"] == "errored"]:
        commit_link = commit_markdown_link(config, result["commit"])
        msg += f'- [`{branch}` errored]({result["url"]}) on {commit_link}'
    return msg


async def report_last_nightlies(config, client):
    """
    Reports last nightlies to all rooms the bot is in
    """
    results = [
        (branch, Nightlies(config, branch).check_if_last_errored_or_changed_to_passed())
        for branch in config.nightlies_branches
    ]
    if all(result is None for _, result in results):
        logger.info(
            "Nothing to report for branches %s", ",".join(config.nightlies_branches)
        )
        return
    msg = generate_message(
        config,
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
    if tasks:
        await asyncio.wait(tasks)
    else:
        logger.warning("I am in no rooms")
