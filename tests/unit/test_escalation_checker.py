import os
import sys
import pytest

# Ensure the root directory is in the sys.path to import agents
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from agents.orchestrator.agent import EscalationChecker


@pytest.mark.asyncio
async def test_escalation_checker_dict_pass(mock_invocation_context):
    checker = EscalationChecker(name="escalation_checker")
    mock_invocation_context.session.state["judge_feedback"] = {"status": "pass"}

    events = []
    async for event in checker._run_async_impl(mock_invocation_context):
        events.append(event)

    assert len(events) == 1
    assert events[0].author == "escalation_checker"
    assert events[0].actions is not None
    assert events[0].actions.escalate is True


@pytest.mark.asyncio
async def test_escalation_checker_str_pass(mock_invocation_context):
    checker = EscalationChecker(name="escalation_checker")
    mock_invocation_context.session.state["judge_feedback"] = '{"status": "pass", "reason": "Good"}'

    events = []
    async for event in checker._run_async_impl(mock_invocation_context):
        events.append(event)

    assert len(events) == 1
    assert events[0].author == "escalation_checker"
    assert events[0].actions is not None
    assert events[0].actions.escalate is True


@pytest.mark.asyncio
async def test_escalation_checker_fail(mock_invocation_context):
    checker = EscalationChecker(name="escalation_checker")
    mock_invocation_context.session.state["judge_feedback"] = {"status": "fail"}

    events = []
    async for event in checker._run_async_impl(mock_invocation_context):
        events.append(event)

    assert len(events) == 1
    assert events[0].author == "escalation_checker"
    assert events[0].actions is None or not events[0].actions.escalate


@pytest.mark.asyncio
async def test_escalation_checker_no_feedback(mock_invocation_context):
    checker = EscalationChecker(name="escalation_checker")

    events = []
    async for event in checker._run_async_impl(mock_invocation_context):
        events.append(event)

    assert len(events) == 1
    assert events[0].author == "escalation_checker"
    assert events[0].actions is None or not events[0].actions.escalate
