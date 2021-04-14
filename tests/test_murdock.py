import datetime
import logging

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


def test_generate_message():
    results = [
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
    msg = generate_message(MockConfig(), "Hello!", results)
    assert (
        msg
        == """Hello! Here is my morning report for the nightlies:

- [`master` passed](https://example.org/passed) on [11fadfcc9d](https://github.com/RIOT-OS/RIOT/commit/11fadfcc9ddac1a6b5051cc93572fac6b9a9d838) after having errored last time
- [`2020.07-branch` errored](https://example.org/errored) on [f9fa738290](https://github.com/RIOT-OS/RIOT/commit/f9fa7382909d4a6096a2d79c0bb4d625ff8389f8)"""
    )
