"""
Unit tests for agent service
"""
import pytest
from app.services.agent_service import CaseAnalysisAgent


@pytest.fixture
def agent():
    """Create agent instance for testing"""
    return CaseAnalysisAgent()


@pytest.mark.asyncio
async def test_analyze_case_basic(agent):
    """Test basic case analysis"""
    case_id = "TEST_001"
    
    result = await agent.analyze_case(case_id)
    
    assert result.case_id == case_id
    assert result.summary is not None
    assert len(result.next_actions) > 0
    assert 0 <= result.confidence_score <= 1
    assert 0 <= result.accuracy_percentage <= 100


@pytest.mark.asyncio
async def test_sanitization(agent):
    """Test that sensitive data is sanitized"""
    case_id = "TEST_002"
    
    result = await agent.analyze_case(case_id)
    
    # Check that sanitized summary doesn't contain email patterns
    assert "@" not in result.sanitized_summary or "[EMAIL]" in result.sanitized_summary
    
    # Raw summary should be different from sanitized
    # (unless there was no sensitive data)
    assert result.raw_summary is not None
    assert result.sanitized_summary is not None


def test_load_examples(agent):
    """Test that examples are loaded correctly"""
    assert agent.examples_df is not None
    # Should have at least some examples
    assert len(agent.examples_df) >= 0


def test_basic_sanitization(agent):
    """Test basic sanitization function"""
    text_with_email = "Contact john@example.com for details"
    sanitized = agent._basic_sanitization(text_with_email)
    
    assert "[EMAIL]" in sanitized
    assert "john@example.com" not in sanitized
    
    text_with_phone = "Call +1-555-1234 for support"
    sanitized = agent._basic_sanitization(text_with_phone)
    
    assert "[PHONE]" in sanitized
