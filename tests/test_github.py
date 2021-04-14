#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2021 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

from murdock_nio_bot.github import Workflow


class MockConfig:
    # use property to make sure the attributes are only read
    @property
    def github_org(self):
        return "RIOT-OS"

    @property
    def github_repo(self):
        return "RIOT"

    @property
    def github_workflows(self):
        return [
            {"name": "release-tests"},
            {"name": "test-on-iotlab"},
            {"name": "test-on-ryot"},
        ]


def test_fetch_workflows():
    config = MockConfig()
    workflows = Workflow.fetch_workflows(config)
    exp_names = {w["name"] for w in config.github_workflows}
    exp_report_xml = {
        w["name"]: w.get("report_xml", False) for w in config.github_workflows
    }
    for workflow in workflows:
        assert workflow.config is config
        assert isinstance(workflow.id, int)
        assert workflow.name in exp_names
        assert workflow.report_xml == exp_report_xml[workflow.name]


def test_workflow_scheduled_runs():
    config = MockConfig()
    workflow = Workflow.fetch_workflows(config)[1]
    for run in workflow.scheduled_runs:
        print(run.conclusion)
        assert isinstance(run.id, int)
