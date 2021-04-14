import datetime
import logging

import pytest

from murdock_nio_bot.github import WorkflowRun
from murdock_nio_bot.murdock import Nightlies, commit_markdown_link, generate_message


class MockConfig:
    # use property to make sure the attributes are only read
    @property
    def nightlies_url(self):
        return "https://ci.riot-os.org/RIOT-OS/RIOT/{branch}/nightlies.json"

    @property
    def result_url(self):
        return "https://ci.riot-os.org/RIOT-OS/RIOT/{branch}/{commit}/output.html"

    @property
    def commit_url(self):
        return "https://github.com/RIOT-OS/RIOT/commit/{commit}"


def test_get_nightlies_real(caplog):
    with caplog.at_level(logging.ERROR):
        nightlies = Nightlies(MockConfig(), "master").get_nightlies()
    if len(nightlies) > 0:
        assert "commit" in nightlies[0]
        assert len(nightlies[0]["commit"]) == 40, "commit not full hash"
        assert int(nightlies[0]["commit"], base=16) > 0, "commit not hex"
        assert "result" in nightlies[0]
        assert "since" in nightlies[0]
        since = datetime.datetime.utcfromtimestamp(nightlies[0]["since"])
        assert since <= datetime.datetime.now(), "invalid timestamp"
    else:
        assert (
            "Unable to GET" in caplog.text or "Unable to decode" in caplog.text
        ), "unexpected log output"


def test_check_if_last__empty(mocker):
    mocker.patch("murdock_nio_bot.murdock.Nightlies.get_nightlies", return_value=[])
    res = Nightlies(MockConfig(), "master").check_if_last_errored_or_changed_to_passed()
    assert res is None


def test_check_if_last__errored(mocker):
    exp_hash = "11fadfcc9ddac1a6b5051cc93572fac6b9a9d838"
    mocker.patch(
        "murdock_nio_bot.murdock.Nightlies.get_nightlies",
        return_value=[
            {
                "result": "errored",
                "commit": exp_hash,
                "since": 1617813041,
            }
        ],
    )
    config = MockConfig()
    res = Nightlies(config, "master").check_if_last_errored_or_changed_to_passed()
    assert res["result"] == "errored"
    assert res["commit"] == exp_hash
    assert res["since"] == datetime.datetime(2021, 4, 7, 16, 30, 41)
    assert res["url"] == config.result_url.format(branch="master", commit=exp_hash)


def test_check_if_last__errored_same_commit(mocker):
    exp_hash = "11fadfcc9ddac1a6b5051cc93572fac6b9a9d838"
    mocker.patch(
        "murdock_nio_bot.murdock.Nightlies.get_nightlies",
        return_value=[
            {
                "result": "errored",
                "commit": exp_hash,
                "since": 1617813041,
            },
            {
                "result": "errored",
                "commit": exp_hash,
                "since": 1617726641,
            },
        ],
    )
    config = MockConfig()
    res = Nightlies(config, "master").check_if_last_errored_or_changed_to_passed()
    assert res is None


def test_check_if_last__passed1(mocker):
    mocker.patch(
        "murdock_nio_bot.murdock.Nightlies.get_nightlies",
        return_value=[
            {
                "result": "passed",
                "commit": "11fadfcc9ddac1a6b5051cc93572fac6b9a9d838",
                "since": 1617813041,
            },
        ],
    )
    res = Nightlies(MockConfig(), "master").check_if_last_errored_or_changed_to_passed()
    assert res is None


def test_check_if_last__passed2(mocker):
    mocker.patch(
        "murdock_nio_bot.murdock.Nightlies.get_nightlies",
        return_value=[
            {
                "result": "passed",
                "commit": "11fadfcc9ddac1a6b5051cc93572fac6b9a9d838",
                "since": 1617813041,
            },
            {
                "result": "passed",
                "commit": "f9fa7382909d4a6096a2d79c0bb4d625ff8389f8",
                "since": 1617726641,
            },
        ],
    )
    res = Nightlies(MockConfig(), "master").check_if_last_errored_or_changed_to_passed()
    assert res is None


def test_check_if_last__passed_prev_errored(mocker):
    exp_hash = "11fadfcc9ddac1a6b5051cc93572fac6b9a9d838"
    mocker.patch(
        "murdock_nio_bot.murdock.Nightlies.get_nightlies",
        return_value=[
            {
                "result": "passed",
                "commit": exp_hash,
                "since": 1617813041,
            },
            {
                "result": "errored",
                "commit": "f9fa7382909d4a6096a2d79c0bb4d625ff8389f8",
                "since": 1617726641,
            },
        ],
    )
    config = MockConfig()
    res = Nightlies(config, "master").check_if_last_errored_or_changed_to_passed()
    assert res["result"] == "passed"
    assert res["commit"] == exp_hash
    assert res["since"] == datetime.datetime(2021, 4, 7, 16, 30, 41)
    assert res["url"] == config.result_url.format(branch="master", commit=exp_hash)


def test_commit_markdown_link():
    config = MockConfig()
    res = commit_markdown_link(config, "93ba8bea3bbd5c8c32d1ccc29ccdf7f86749c690")
    exp_commit_url = config.commit_url.format(
        commit="93ba8bea3bbd5c8c32d1ccc29ccdf7f86749c690"
    )
    assert res == f"[93ba8bea3b]({exp_commit_url})"


@pytest.mark.parametrize(
    "workflows",
    [
        None,
        [
            (
                "release-tests",
                WorkflowRun(
                    MockConfig(),
                    2485316784,
                    "c89739f7f0a339ba22e8f5cc92ce74a4e0c99adc",
                    "failure",
                    "https://github.com/RIOT-OS/RIOT/actions/runs/2485316784",
                ),
            ),
            (
                "test-on-iotlab",
                WorkflowRun(
                    MockConfig(),
                    1002909749,
                    "584aa98d7afed1214dd7858fcfb742545d5c2fb2",
                    "success",
                    "https://github.com/RIOT-OS/RIOT/actions/runs/1002909749",
                ),
            ),
        ],
    ],
)
def test_generate_message(workflows):
    nightlies = [
        (
            "master",
            {
                "result": "passed",
                "url": "https://example.org/passed",
                "commit": "11fadfcc9ddac1a6b5051cc93572fac6b9a9d838",
                "since": 1617813041,
            },
        ),
        (
            "2020.07-branch",
            {
                "result": "errored",
                "url": "https://example.org/errored",
                "commit": "f9fa7382909d4a6096a2d79c0bb4d625ff8389f8",
                "since": 1617726641,
            },
        ),
    ]
    exp_msg = "Hello! Here is my morning report for the nightlies"

    if workflows:
        exp_msg += " and GitHub workflows"
    exp_msg += ":\n\n"

    exp_msg += "- [`master` nightlies passed](https://example.org/passed) on [11fadfcc9d](https://github.com/RIOT-OS/RIOT/commit/11fadfcc9ddac1a6b5051cc93572fac6b9a9d838) after having errored last time\n"
    if workflows:
        exp_msg += "- [`test-on-iotlab` workflow passed](https://github.com/RIOT-OS/RIOT/actions/runs/1002909749) on [584aa98d7a](https://github.com/RIOT-OS/RIOT/commit/584aa98d7afed1214dd7858fcfb742545d5c2fb2) after having errored last time\n"
    exp_msg += "- [`2020.07-branch` nightlies errored](https://example.org/errored) on [f9fa738290](https://github.com/RIOT-OS/RIOT/commit/f9fa7382909d4a6096a2d79c0bb4d625ff8389f8)\n"
    if workflows:
        exp_msg += "- [`release-tests` workflow errored](https://github.com/RIOT-OS/RIOT/actions/runs/2485316784) on [c89739f7f0](https://github.com/RIOT-OS/RIOT/commit/c89739f7f0a339ba22e8f5cc92ce74a4e0c99adc)\n"

    msg = generate_message(MockConfig(), "Hello!", nightlies, workflows)
    assert msg == exp_msg
