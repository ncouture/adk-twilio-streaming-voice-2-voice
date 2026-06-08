import pytest
from unittest.mock import MagicMock
from google.adk.agents.invocation_context import InvocationContext

@pytest.fixture
def mock_invocation_context():
    """Provides a mocked InvocationContext for testing ADK agents."""
    ctx = MagicMock(spec=InvocationContext)
    ctx.session = MagicMock()
    ctx.session.state = {}
    return ctx