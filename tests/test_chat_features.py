"""Tests for chat memory, guidance, and intent formatting."""

from agent.capabilities import build_capability_help, get_capability_examples
from agent.intent import Intent, IntentType, get_intent_description
from agent.state import AgentState


class TestConversationMemory:
    """Test persistent conversation memory helpers."""

    def test_add_conversation_message_and_read_recent_history(self):
        """Recent history preserves order and role/content pairs."""
        state = AgentState()

        state.add_conversation_message("human", "scan hot sol memes")
        state.add_conversation_message("ai", "I can scan Solana meme tokens now.")

        assert state.conversation_history[0].role == "human"
        assert state.conversation_history[1].role == "ai"
        assert state.get_recent_conversation() == [
            ("human", "scan hot sol memes"),
            ("ai", "I can scan Solana meme tokens now."),
        ]

    def test_recent_history_respects_limit(self):
        """Recent conversation helper returns only the requested tail."""
        state = AgentState()

        for index in range(6):
            state.add_conversation_message("human", f"message-{index}")

        assert state.get_recent_conversation(limit=3) == [
            ("human", "message-3"),
            ("human", "message-4"),
            ("human", "message-5"),
        ]


class TestCapabilityGuidance:
    """Test skill/capability-driven help text."""

    def test_capability_examples_include_supported_actions(self):
        """Examples expose the main Solana meme workflows."""
        examples = get_capability_examples()

        assert any("scan" in example.lower() for example in examples)
        assert any("buy" in example.lower() for example in examples)
        assert any("auto invest 0.01 sol" in example.lower() for example in examples)
        assert any(
            "portfolio" in example.lower() or "status" in example.lower() for example in examples
        )

    def test_capability_examples_with_limit_keep_auto_invest_visible(self):
        """The startup banner limit should still surface auto-invest guidance."""
        examples = get_capability_examples(limit=6)

        assert any("auto invest 0.01 sol" in example.lower() for example in examples)

    def test_capability_help_mentions_natural_language_guidance(self):
        """Help text encourages free-form interaction instead of rigid commands."""
        help_text = build_capability_help()

        assert "natural language" in help_text.lower()
        assert "scan" in help_text.lower()
        assert "analyze" in help_text.lower()
        assert "auto invest" in help_text.lower()


class TestIntentDescriptions:
    """Test human-readable intent display strings."""

    def test_auto_invest_description_prefers_sol_budget_when_present(self):
        """SOL-denominated auto-invest requests should be described in SOL."""
        intent = Intent(
            type=IntentType.AUTO_INVEST,
            params={"budget_sol": 0.01, "budget_usd": 1.5},
            confidence=0.9,
            raw_input="auto invest 0.01 sol",
        )

        description = get_intent_description(intent)

        assert "0.01 SOL" in description
        assert "1.50 USDT" in description
