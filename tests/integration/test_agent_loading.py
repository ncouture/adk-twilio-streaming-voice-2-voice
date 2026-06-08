import os
import sys

# Ensure the root directory is in the sys.path to import agents
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_orchestrator_agent_loading():
    """Verify the orchestrator agents can be imported and initialized without errors."""
    from agents.orchestrator.agent import (
        root_agent,
        research_loop,
        researcher,
        judge,
        content_builder,
        escalation_checker
    )
    
    assert root_agent is not None
    assert root_agent.name == "course_creation_pipeline"
    
    assert research_loop is not None
    assert research_loop.name == "research_loop"
    
    # Check that it loaded remote sub-agents correctly
    assert researcher.name == "researcher"
    assert judge.name == "judge"
    assert content_builder.name == "content_builder"
    
    # Check orchestration sub-agent
    assert escalation_checker.name == "escalation_checker"
