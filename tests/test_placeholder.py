"""Placeholder tests to verify project structure."""

import os
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_project_structure():
    """Verify core directories exist."""
    required_dirs = ["tests", "agent", "cli", "skills"]
    for dir_name in required_dirs:
        assert (ROOT / dir_name).exists(), f"Directory {dir_name} should exist"


def test_env_loading():
    """Verify .env.example exists and contains expected config sections."""
    env_example = ROOT / ".env.example"
    assert env_example.exists(), ".env.example should exist"

    content = env_example.read_text()
    expected_sections = [
        "# Bitget Wallet API",
        "# Solana RPC",
        "# Wallet Management",
        "# Deep Agents",
    ]
    for section in expected_sections:
        assert section in content, f"Section '{section}' should be in .env.example"


def test_requirements_file():
    """Verify requirements.txt exists and has content."""
    requirements = ROOT / "requirements.txt"
    assert requirements.exists(), "requirements.txt should exist"

    content = requirements.read_text()
    assert len(content.strip()) > 0, "requirements.txt should have content"
    assert "deepagents" in content or "langchain" in content, (
        "Should include agent framework"
    )
