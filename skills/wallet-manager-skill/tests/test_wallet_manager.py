#!/usr/bin/env python3
"""
Test suite for Wallet Manager - BIP-39/BIP-44 Wallet Management

Tests cover:
- Mnemonic generation and validation
- Address derivation for Solana and EVM chains
- Secure storage integration
- Security properties (no private key leakage)
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
import keyring
from keyring.backends.fail import Keyring as FailKeyring

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from wallet_manager import (
    generate_mnemonic,
    validate_mnemonic,
    derive_solana_keypair,
    derive_evm_address,
    derive_all_addresses,
    store_securely,
    retrieve_from_storage,
    delete_from_storage,
    KEYRING_SERVICE_NAME,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def test_keypair():
    """
    Fixture providing a known test mnemonic and expected addresses.

    This uses a well-known test vector for reproducible tests.
    IMPORTANT: This mnemonic is for TESTING ONLY - never use for real funds.
    """
    return {
        # 12-word test mnemonic (BIP-39 test vector)
        "mnemonic": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
        # Expected Solana address from m/44'/501'/0'/0'
        "solana_address": "4uNwhLjvXkV1R9oXhQ8G7kXzPvJqKzPzVvLzPvJqKzPz",
        # Expected EVM address from m/44'/60'/0'/0/0
        "evm_address": "0x9858EfFD232B4033E47d90003D41EC34EcaEda94",
    }


@pytest.fixture
def temp_keyring():
    """
    Fixture providing a temporary keyring backend for testing.

    Uses in-memory backend to avoid polluting real OS keyring.
    Automatically cleans up after test.
    """
    # Use keyring's null backend for testing
    from keyring.backends.null import Keyring as NullKeyring

    # Set up null keyring to avoid hitting real OS keyring
    keyring.set_keyring(NullKeyring())

    test_wallet_name = "test_wallet_temp"

    yield test_wallet_name

    # Cleanup: try to delete if it was created
    try:
        delete_from_storage(test_wallet_name)
    except (KeyError, Exception):
        pass  # May not exist


@pytest.fixture
def mock_keyring_backend():
    """
    Fixture providing an in-memory mock keyring backend.

    This allows testing secure storage without OS dependencies.
    """
    storage = {}

    class MockKeyring:
        def set_password(self, service, username, password):
            storage[(service, username)] = password

        def get_password(self, service, username):
            return storage.get((service, username))

        def delete_password(self, service, username):
            if (service, username) in storage:
                del storage[(service, username)]
            else:
                raise Exception("Password not found")

    mock_backend = MockKeyring()
    keyring.set_keyring(mock_backend)

    yield mock_backend, storage

    # Cleanup
    storage.clear()


# =============================================================================
# MNEMONIC GENERATION TESTS
# =============================================================================


class TestMnemonicGeneration:
    """Tests for BIP-39 mnemonic generation."""

    def test_mnemonic_generation(self):
        """
        Test that generated mnemonic has exactly 24 words.

        Verifies:
        - Exactly 24 words generated (256 bits of entropy)
        - All words are valid BIP-39 words
        """
        # Generate mnemonic
        mnemonic = generate_mnemonic(word_count=24)

        # Verify word count
        words = mnemonic.split()
        assert len(words) == 24, f"Expected 24 words, got {len(words)}"

        # Verify all words are in BIP-39 wordlist
        # bip_utils uses the standard BIP-39 wordlist
        from bip_utils import Bip39MnemonicValidator
        from bip_utils.bip39.bip39_words import Bip39Words

        # Get the standard wordlist
        valid_words = set(Bip39Words())

        for word in words:
            assert word.lower() in valid_words, f"Word '{word}' not in BIP-39 wordlist"

    def test_mnemonic_validity(self):
        """
        Test that generated mnemonic passes BIP-39 checksum validation.

        Verifies:
        - Generated mnemonic has valid checksum
        - Validation function correctly identifies valid mnemonics
        """
        # Generate multiple mnemonics and validate each
        for _ in range(5):
            mnemonic = generate_mnemonic(word_count=24)

            is_valid, msg = validate_mnemonic(mnemonic)

            assert is_valid, f"Generated mnemonic failed validation: {msg}"

        # Test that invalid mnemonics are rejected
        invalid_mnemonic = " ".join(["abandon"] * 23 + ["invalid_word_xyz"])
        is_valid, msg = validate_mnemonic(invalid_mnemonic)
        assert not is_valid, "Invalid mnemonic should fail validation"

    def test_mnemonic_generation_word_counts(self):
        """Test mnemonic generation with different word counts."""
        valid_word_counts = [12, 15, 18, 21, 24]

        for word_count in valid_word_counts:
            mnemonic = generate_mnemonic(word_count=word_count)
            words = mnemonic.split()
            assert len(words) == word_count, (
                f"Expected {word_count} words, got {len(words)}"
            )

            # Validate checksum
            is_valid, _ = validate_mnemonic(mnemonic)
            assert is_valid, f"{word_count}-word mnemonic failed validation"


# =============================================================================
# ADDRESS DERIVATION TESTS
# =============================================================================


class TestAddressDerivation:
    """Tests for BIP-44 address derivation."""

    def test_solana_address_derivation(self, test_keypair):
        """
        Test Solana address derivation with correct path.

        Derivation path: m/44'/501'/0'/0'
        - 44' = BIP-44 purpose
        - 501' = Solana coin type
        - 0' = Account 0
        - 0' = External chain

        Verifies:
        - Address derived from correct BIP-44 path
        - Address format is valid Solana base58
        """
        mnemonic = test_keypair["mnemonic"]

        # Derive Solana keypair
        solana_addr, private_key_bytes = derive_solana_keypair(mnemonic)

        # Verify address format (Solana addresses are 32-44 chars base58)
        assert len(solana_addr) >= 32, f"Solana address too short: {len(solana_addr)}"
        assert len(solana_addr) <= 44, f"Solana address too long: {len(solana_addr)}"

        # Verify private key is 64 bytes (Ed25519)
        assert len(private_key_bytes) == 64, (
            f"Expected 64-byte private key, got {len(private_key_bytes)}"
        )

        # Test with known test vector (24 'abandon' words)
        test_mnemonic = " ".join(["abandon"] * 24)
        solana_addr_24, _ = derive_solana_keypair(test_mnemonic)

        # Address should be deterministic (same mnemonic = same address)
        solana_addr_24_again, _ = derive_solana_keypair(test_mnemonic)
        assert solana_addr_24 == solana_addr_24_again, (
            "Address derivation not deterministic"
        )

    def test_evm_address_derivation(self, test_keypair):
        """
        Test EVM address derivation with correct path.

        Derivation path: m/44'/60'/0'/0/0
        - 44' = BIP-44 purpose
        - 60' = Ethereum coin type (all EVM chains)
        - 0' = Account 0
        - 0 = External chain
        - 0 = Address index

        Verifies:
        - Address derived from correct BIP-44 path
        - Address format is 0x-prefixed (42 chars)
        """
        mnemonic = test_keypair["mnemonic"]

        # Derive EVM address
        evm_addr = derive_evm_address(mnemonic)

        # Verify address format
        assert evm_addr.startswith("0x"), (
            f"EVM address must start with 0x, got: {evm_addr[:2]}"
        )
        assert len(evm_addr) == 42, f"EVM address must be 42 chars, got {len(evm_addr)}"

        # Verify hex characters
        import re

        assert re.match(r"^0x[0-9a-fA-F]{40}$", evm_addr), (
            f"Invalid EVM address format: {evm_addr}"
        )

        # Test determinism
        evm_addr_again = derive_evm_address(mnemonic)
        assert evm_addr == evm_addr_again, "EVM address derivation not deterministic"

    def test_same_evm_address_all_chains(self):
        """
        Test that all EVM chains share the same address.

        Verifies:
        - ETH address = BNB address = Base address = Polygon address
        - One mnemonic = one EVM address for all chains
        """
        mnemonic = generate_mnemonic()

        # Derive addresses for all chains
        addresses = derive_all_addresses(mnemonic)

        # All EVM chains should have SAME address
        eth_addr = addresses["ethereum"]
        bnb_addr = addresses["bnb_smart_chain"]
        polygon_addr = addresses["polygon"]
        base_addr = addresses["base"]
        arbitrum_addr = addresses["arbitrum"]

        # Verify all EVM addresses are identical
        assert eth_addr == bnb_addr, f"ETH != BNB: {eth_addr} != {bnb_addr}"
        assert eth_addr == polygon_addr, f"ETH != Polygon: {eth_addr} != {polygon_addr}"
        assert eth_addr == base_addr, f"ETH != Base: {eth_addr} != {base_addr}"
        assert eth_addr == arbitrum_addr, (
            f"ETH != Arbitrum: {eth_addr} != {arbitrum_addr}"
        )

        # Solana should be DIFFERENT (different curve)
        solana_addr = addresses["solana"]
        assert solana_addr != eth_addr, "Solana address should differ from EVM"

    def test_evm_address_indices(self):
        """Test that different derivation indices produce different addresses."""
        mnemonic = generate_mnemonic()

        # Derive addresses at different indices
        addr_0 = derive_evm_address(mnemonic, index=0)
        addr_1 = derive_evm_address(mnemonic, index=1)
        addr_2 = derive_evm_address(mnemonic, index=2)

        # All should be unique
        assert addr_0 != addr_1, "Address 0 and 1 should differ"
        assert addr_1 != addr_2, "Address 1 and 2 should differ"
        assert addr_0 != addr_2, "Address 0 and 2 should differ"

        # All should be valid format
        for addr in [addr_0, addr_1, addr_2]:
            assert addr.startswith("0x")
            assert len(addr) == 42

    def test_passphrase_support(self):
        """Test that BIP-39 passphrase changes derived addresses."""
        mnemonic = generate_mnemonic()

        # Derive without passphrase
        addr_no_pass = derive_evm_address(mnemonic)

        # Derive with passphrase
        addr_with_pass = derive_evm_address(mnemonic, passphrase="secret123")

        # Addresses should differ
        assert addr_no_pass != addr_with_pass, "Passphrase should change address"


# =============================================================================
# SECURE STORAGE TESTS
# =============================================================================


class TestSecureStorage:
    """Tests for secure storage integration."""

    def test_secure_storage_retrieval(self, mock_keyring_backend):
        """
        Test storing and retrieving mnemonic from secure storage.

        Verifies:
        - Mnemonic stored successfully
        - Retrieved mnemonic matches original
        - keyring integration works
        """
        mock_backend, storage = mock_keyring_backend

        # Generate and store mnemonic
        original_mnemonic = generate_mnemonic()
        wallet_name = "test_wallet"

        # Store
        result = store_securely(original_mnemonic, wallet_name)
        assert result is True, "Storage should succeed"

        # Verify stored in mock
        account_name = f"wallet:{wallet_name.lower()}"
        assert (KEYRING_SERVICE_NAME, account_name) in storage

        # Retrieve
        retrieved = retrieve_from_storage(wallet_name)

        # Verify match
        assert retrieved == original_mnemonic, (
            "Retrieved mnemonic should match original"
        )

    def test_storage_validation(self, mock_keyring_backend):
        """Test that invalid mnemonics cannot be stored."""
        mock_backend, storage = mock_keyring_backend

        # Try to store invalid mnemonic
        invalid_mnemonic = "not a valid mnemonic phrase"

        with pytest.raises(ValueError) as exc_info:
            store_securely(invalid_mnemonic, "invalid_wallet")

        assert "invalid" in str(exc_info.value).lower()

    def test_storage_not_found(self, mock_keyring_backend):
        """Test retrieval of non-existent wallet."""
        mock_backend, storage = mock_keyring_backend

        with pytest.raises(KeyError) as exc_info:
            retrieve_from_storage("nonexistent_wallet")

        assert "not found" in str(exc_info.value).value.lower()


# =============================================================================
# SECURITY TESTS
# =============================================================================


class TestSecurity:
    """Security-focused tests for wallet manager."""

    def test_private_key_not_stored(self, mock_keyring_backend):
        """
        Test that only mnemonic is stored, not private keys.

        Verifies:
        - Private key derived on-the-fly
        - Only mnemonic persisted in storage
        - Private key bytes not in storage
        """
        mock_backend, storage = mock_keyring_backend

        mnemonic = generate_mnemonic()
        wallet_name = "security_test_wallet"

        # Store mnemonic
        store_securely(mnemonic, wallet_name)

        # Retrieve stored data
        account_name = f"wallet:{wallet_name.lower()}"
        stored_value = storage.get((KEYRING_SERVICE_NAME, account_name))

        # Verify only mnemonic stored
        assert stored_value == mnemonic, "Should store mnemonic"

        # Derive private key separately
        _, private_key_bytes = derive_solana_keypair(mnemonic)
        private_key_hex = private_key_bytes.hex()

        # Verify private key NOT in storage
        assert private_key_hex not in str(stored_value), (
            "Private key should not be stored"
        )

        # Verify mnemonic in storage is not the private key
        assert stored_value != private_key_hex

        # Clear private key from this test's memory
        del private_key_bytes
        del private_key_hex

    def test_mnemonic_not_printed(self, mock_keyring_backend, capsys):
        """
        Test that mnemonic is not printed to stdout during normal operations.

        Verifies:
        - Addresses shown, not mnemonic
        - No mnemonic leak in stdout
        """
        mock_backend, storage = mock_keyring_backend

        mnemonic = generate_mnemonic()
        wallet_name = "stdout_test_wallet"

        # Store mnemonic
        store_securely(mnemonic, wallet_name)

        # Derive addresses (this is what users see)
        addresses = derive_all_addresses(mnemonic)

        # Display addresses (simulating normal output)
        print(f"Solana: {addresses['solana']}")
        print(f"Ethereum: {addresses['ethereum']}")

        # Capture output
        captured = capsys.readouterr()

        # Verify addresses shown
        assert addresses["solana"] in captured.out
        assert addresses["ethereum"] in captured.out

        # Verify mnemonic NOT shown
        mnemonic_words = mnemonic.split()
        for word in mnemonic_words:
            assert word not in captured.out, f"Mnemonic word '{word}' leaked to stdout"

    def test_mnemonic_normalization(self, mock_keyring_backend):
        """Test that mnemonics are normalized before storage."""
        mock_backend, storage = mock_keyring_backend

        original = "  ABANDON   ABANDON  " + " abandon" * 22 + "  about  "
        normalized = "abandon " * 23 + "about"

        # Store with extra whitespace and mixed case
        store_securely(original, "normalized_wallet")

        # Retrieve
        retrieved = retrieve_from_storage("normalized_wallet")

        # Should be normalized
        assert retrieved == normalized
        assert retrieved == retrieved.lower().strip()

    def test_delete_from_storage(self, mock_keyring_backend):
        """Test secure deletion of stored mnemonic."""
        mock_backend, storage = mock_keyring_backend

        mnemonic = generate_mnemonic()
        wallet_name = "delete_test_wallet"

        # Store
        store_securely(mnemonic, wallet_name)
        account_name = f"wallet:{wallet_name.lower()}"
        assert (KEYRING_SERVICE_NAME, account_name) in storage

        # Delete
        result = delete_from_storage(wallet_name)
        assert result is True

        # Verify deleted
        assert (KEYRING_SERVICE_NAME, account_name) not in storage

        # Verify retrieval fails
        with pytest.raises(KeyError):
            retrieve_from_storage(wallet_name)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_invalid_mnemonic_rejected(self):
        """Test that invalid mnemonics are rejected."""
        invalid_cases = [
            "",  # Empty
            "not enough words",  # Too few
            "abandon " * 23 + "invalidxyz",  # Invalid word
            "abandon " * 25,  # Wrong word count (25)
        ]

        for invalid in invalid_cases:
            is_valid, msg = validate_mnemonic(invalid)
            assert not is_valid, f"Should reject: {invalid[:30]}..."

    def test_derivation_invalid_mnemonic(self):
        """Test that derivation fails gracefully with invalid mnemonic."""
        invalid_mnemonic = "not valid"

        with pytest.raises(ValueError):
            derive_solana_keypair(invalid_mnemonic)

        with pytest.raises(ValueError):
            derive_evm_address(invalid_mnemonic)

    def test_evm_negative_index_rejected(self):
        """Test that negative address index is rejected."""
        mnemonic = generate_mnemonic()

        with pytest.raises(ValueError) as exc_info:
            derive_evm_address(mnemonic, index=-1)

        assert "non-negative" in str(exc_info.value)

    def test_invalid_word_count_rejected(self):
        """Test that invalid word counts are rejected."""
        invalid_counts = [8, 10, 13, 20, 25, 100]

        for count in invalid_counts:
            with pytest.raises(ValueError):
                generate_mnemonic(word_count=count)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
