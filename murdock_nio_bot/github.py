import logging
import os

from agithub.GitHub import GitHub

from murdock_nio_bot.errors import ConfigError
from murdock_nio_bot.storage import Storage

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

logger = logging.getLogger()


class Workflow:
    def __init__(self, config, name, id, report_xml=False):
        self.config = config
        self.name = name
        self.id = id
        self.report_xml = report_xml

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<{}: {}>".format(type(self).__name__, self)

    @staticmethod
    def fetch_workflows(config):
        status, data = (
            GitHub(token=GITHUB_TOKEN)
            .repos[config.github_org][config.github_repo]
            .actions.workflows.get()
        )
        if status != 200:
            logger.error("Unable to fetch workflow list from Github")
            return []
        workflow_list = data["workflows"]
        workflows = {w["name"]: w for w in config.github_workflows}
        available_names = {w["name"] for w in workflow_list}
        for workflow in workflows:
            if workflow not in available_names:
                raise ConfigError(f"{workflow['name']} is not in a workflow")
        res = []
        for workflow in workflow_list:
            name = workflow["name"]
            if name not in workflows:
                continue
            res.append(Workflow(config, id=workflow["id"], **workflows[name]))
        return res

    @property
    def scheduled_runs(self):
        status, data = (
            GitHub(token=GITHUB_TOKEN)
            .repos[self.config.github_org][self.config.github_repo]
            .actions.workflows[self.id]
            .runs.get()
        )
        if status != 200:
            logger.error("Unable to fetch workflow runs from Github")
            return []
        return [
            WorkflowRun(self.config, **r)
            for r in data["workflow_runs"]
            if r["event"] == "schedule" and r["status"] == "completed"
        ]

    def check_if_last_errored_or_changed_to_passed(self):
        results = self.scheduled_runs
        store = Storage(self.config.database)
        if len(results) == 0:
            return None
        if results[0].commit == store.get_last_run_commit(self.id):
            return None
        if results[0].conclusion == "failure" or (
            len(results) > 1
            and results[1].conclusion == "failure"
            and results[0].conclusion == "success"
        ):
            result = results[0]
            store.set_last_run_commit(self.id, results[0].commit)
            return result
        return None


class WorkflowRun:
    def __init__(self, config, id, head_sha, conclusion, html_url, *args, **kwargs):
        self.config = config
        self.id = id
        self.commit = head_sha
        self.conclusion = conclusion
        self.html_url = html_url
