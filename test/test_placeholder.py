"""Placeholder tests to verify pytest configuration works."""

import os
from pathlib import Path


def test_project_structure():
    """Verify that core project directories exist.

    This test ensures the basic project structure is in place
    by checking for expected directories at the project root.
    """
    root_dir = Path(__file__).parent.parent

    # Check core directories exist
    assert root_dir.exists(), "Project root directory should exist"
    assert (root_dir / "test").exists(), "test directory should exist"
    assert (root_dir / "agent").exists(), "agent directory should exist"
    assert (root_dir / "cli").exists(), "cli directory should exist"
    assert (root_dir / "skills").exists(), "skills directory should exist"


def test_env_loading():
    """Verify that .env.example can be parsed correctly.

    This test reads and parses the .env.example file to ensure
    the configuration template is present and properly formatted.
    """
    root_dir = Path(__file__).parent.parent
    env_example_path = root_dir / ".env.example"

    # Check file exists
    assert env_example_path.exists(), ".env.example file should exist"

    # Read and verify content
    with open(env_example_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify key configuration sections exist
    assert "# Bitget Wallet API" in content, "Should have Bitget Wallet API section"
    assert "# Solana RPC" in content, "Should have Solana RPC section"
    assert "SOLANA_RPC_URL=" in content, "Should have SOLANA_RPC_URL config"
    assert "ANTHROPIC_API_KEY=" in content, "Should have ANTHROPIC_API_KEY config"
    assert "DEFAULT_SLIPPAGE=" in content, "Should have DEFAULT_SLIPPAGE config"


def test_requirements_file():
    """Verify that requirements.txt exists and is readable.

    This test ensures the project dependencies file is present
    and contains expected package entries.
    """
    root_dir = Path(__file__).parent.parent
    requirements_path = root_dir / "requirements.txt"

    # Check file exists
    assert requirements_path.exists(), "requirements.txt should exist"

    # Read and verify it has content
    with open(requirements_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify it contains package definitions (not just comments)
    lines = [
        line.strip()
        for line in content.split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(lines) > 0, "requirements.txt should contain package definitions"
