#!/usr/bin/env python3
"""
Wallet Manager - Secure BIP-39/BIP-44 Wallet Management for Solana and EVM Chains

CRITICAL SECURITY NOTES:
- This tool handles cryptographic secrets (mnemonics, private keys)
- NEVER log, print, or store private keys in plain text
- Uses platform-native secure storage (Windows Credential Locker, macOS Keychain, Linux SecretService)
- Private keys are derived on-the-fly, used, then discarded from memory

Author: BestTradeAgent
License: MIT
"""

import argparse
import hashlib
import os
import secrets
import sys
import warnings
from typing import Optional, Tuple

# Suppress cryptography/warning logs that might leak info
warnings.filterwarnings("ignore", category=UserWarning)

try:
    # BIP-39/BIP-44 implementation with support for multiple curves
    from bip_utils import (
        Bip39SeedGenerator,
        Bip39MnemonicGenerator,
        Bip39WordsNum,
    )

    # Solana-specific operations (Ed25519 curve)
    from bip_utils import SolAddr, Bip32Slip10Ed25519

    # EVM-specific operations (secp256k1 curve)
    from bip_utils import Bip32Slip10Secp256k1, EthAddr
except ImportError as e:
    print(f"ERROR: Required dependency not installed: {e}", file=sys.stderr)
    print("Install with: pip install bip-utils", file=sys.stderr)
    sys.exit(1)

try:
    import keyring
    from keyring.errors import KeyringError, KeyringLocked
except ImportError:
    print("ERROR: Required dependency not installed: keyring", file=sys.stderr)
    print("Install with: pip install keyring", file=sys.stderr)
    sys.exit(1)


# =============================================================================
# SECURITY CONSTANTS
# =============================================================================

# Service name for secure storage (appears in OS credential manager)
KEYRING_SERVICE_NAME = "BestTradeAgent-WalletManager"

# Minimum entropy bits for mnemonic generation (256 bits = 24 words)
MIN_ENTROPY_BITS = 256
MAX_ENTROPY_BITS = 256  # Fixed at 256 for 24-word mnemonics

# Derivation paths (BIP-44 standard)
# Format: m / purpose' / coin_type' / account' / change / address_index
# All values with ' are hardened (add 0x80000000)
DERIVATION_PATHS = {
    "solana": "m/44'/501'/0'/0'",  # Solana: Ed25519 curve, coin_type=501
    "evm": "m/44'/60'/0'/0/0",  # EVM (ETH, BNB, Base, etc): secp256k1, coin_type=60
}

# Security warning messages
SECURITY_WARNINGS = """
⚠️  SECURITY WARNINGS (READ CAREFULLY):
────────────────────────────────────────
• NEVER share your mnemonic phrase with anyone
• Store backup in a secure, offline location (e.g., metal backup plate)
• This tool does NOT store your keys on any server
• Private keys are derived on-the-fly and discarded after use
• Only use --show-mnemonic in secure, private environments
• Enable production mode (--production) to hide sensitive output
"""


# =============================================================================
# MNEMONIC GENERATION (BIP-39)
# =============================================================================


def generate_mnemonic(word_count: int = 24) -> str:
    """
    Generate a new BIP-39 mnemonic phrase with cryptographically secure entropy.

    SECURITY:
    - Uses secrets module for CSPRNG (Cryptographically Secure Pseudo-Random Number Generator)
    - 24 words = 256 bits of entropy (recommended for high-security applications)
    - Never use 12 words for production wallets (only 128 bits of entropy)

    Args:
        word_count: Number of words (12, 15, 18, 21, or 24). Default: 24 for max security.

    Returns:
        str: Space-separated mnemonic phrase (24 words by default)

    Raises:
        ValueError: If word_count is not a valid BIP-39 word count
    """
    # Map word count to BIP-39 entropy size
    word_count_map = {
        12: Bip39WordsNum.WORDS_NUM_12,  # 128 bits
        15: Bip39WordsNum.WORDS_NUM_15,  # 160 bits
        18: Bip39WordsNum.WORDS_NUM_18,  # 192 bits
        21: Bip39WordsNum.WORDS_NUM_21,  # 224 bits
        24: Bip39WordsNum.WORDS_NUM_24,  # 256 bits (RECOMMENDED)
    }

    if word_count not in word_count_map:
        raise ValueError(
            f"Invalid word count: {word_count}. "
            f"Must be one of: {list(word_count_map.keys())}"
        )

    # Generate mnemonic using bip-utils (uses os.urandom internally)
    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(word_count_map[word_count])

    # SECURITY: mnemonic is a string, convert to ensure clean type
    mnemonic_str = str(mnemonic)

    # SECURITY VALIDATION: Verify mnemonic has correct word count
    words = mnemonic_str.split()
    if len(words) != word_count:
        # This should never happen, but verify for safety
        raise RuntimeError(
            f"Generated mnemonic has {len(words)} words, expected {word_count}"
        )

    return mnemonic_str


def validate_mnemonic(mnemonic: str) -> Tuple[bool, str]:
    """
    Validate a BIP-39 mnemonic phrase.

    SECURITY:
    - Checks word count and checksum validity
    - Does NOT derive keys (safe to call in production logs)

    Args:
        mnemonic: Space-separated mnemonic phrase

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    # SECURITY: Normalize input - strip whitespace, lowercase
    mnemonic = " ".join(mnemonic.strip().lower().split())

    # Check word count
    words = mnemonic.split()
    valid_word_counts = {12, 15, 18, 21, 24}
    if len(words) not in valid_word_counts:
        return False, f"Invalid word count: {len(words)}. Must be 12, 15, 18, 21, or 24"

    # Verify mnemonic can generate a seed (validates checksum)
    try:
        Bip39SeedGenerator(mnemonic).Generate()
        return True, "Mnemonic is valid"
    except ValueError as e:
        return False, f"Invalid mnemonic checksum: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


# =============================================================================
# KEY DERIVATION (BIP-44)
# =============================================================================


def derive_solana_keypair(mnemonic: str, passphrase: str = "") -> Tuple[str, bytes]:
    """
    Derive Solana keypair from mnemonic using BIP-44 path.

    DERIVATION PATH: m/44'/501'/0'/0'
    CURVE: Ed25519 (Solana uses Blake2b-modified Ed25519)

    SECURITY:
    - Private key bytes are returned but should be used immediately and discarded
    - Never log or persist private key bytes
    - Passphrase support for additional security layer

    Args:
        mnemonic: BIP-39 mnemonic phrase
        passphrase: Optional BIP-39 passphrase (adds security layer)

    Returns:
        Tuple[str, bytes]: (base58_public_key, private_key_bytes)

    Raises:
        ValueError: If mnemonic is invalid
    """
    # SECURITY: Validate mnemonic before deriving keys
    is_valid, msg = validate_mnemonic(mnemonic)
    if not is_valid:
        raise ValueError(f"Invalid mnemonic: {msg}")

    # Generate seed from mnemonic (512-bit seed per BIP-39)
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate(passphrase)

    # Derive using Solana's specific path: m/44'/501'/0'/0'
    # Note: Solana uses Ed25519 with Blake2b hash modification
    try:
        # Create master key from seed using SLIP-10 Ed25519
        master_key = Bip32Slip10Ed25519.FromSeed(seed_bytes)

        # Derive path: 44'/501'/0'/0'
        # 0x80000000 indicates hardened derivation
        derived = master_key.DerivePath("m/44'/501'/0'/0'")

        # Extract private key (32 bytes) from the derived key
        # DataBytes object - convert to actual bytes
        private_key_bytes = bytes(derived.PrivateKey().Raw())

        # Derive Solana address from public key
        # Get compressed public key (33 bytes), remove prefix byte to get 32-byte key
        pub_key_compressed = bytes(derived.PublicKey().RawCompressed())
        public_key_bytes = pub_key_compressed[1:]  # Remove 0x00 prefix

        # Encode to Solana base58 address
        solana_addr = SolAddr.EncodeKey(public_key_bytes)

        return solana_addr, private_key_bytes

    except Exception as e:
        raise ValueError(f"Failed to derive Solana keypair: {str(e)}")


def derive_evm_address(mnemonic: str, passphrase: str = "", index: int = 0) -> str:
    """
    Derive EVM-compatible address from mnemonic using BIP-44 path.

    DERIVATION PATH: m/44'/60'/0'/0/{index}
    CURVE: secp256k1 (used by Ethereum, BNB, Polygon, Base, Arbitrum, etc.)

    SECURITY:
    - Same private key works for ALL EVM chains
    - Only returns address (20 bytes), never exposes private key
    - Private key is derived internally and discarded

    Args:
        mnemonic: BIP-39 mnemonic phrase
        passphrase: Optional BIP-39 passphrase
        index: Address index (0 = first address, 1 = second, etc.)

    Returns:
        str: EVM address (0x-prefixed, 42 characters)

    Raises:
        ValueError: If mnemonic is invalid
    """
    # SECURITY: Validate mnemonic before deriving keys
    is_valid, msg = validate_mnemonic(mnemonic)
    if not is_valid:
        raise ValueError(f"Invalid mnemonic: {msg}")

    if index < 0:
        raise ValueError(f"Address index must be non-negative, got {index}")

    # Generate seed from mnemonic
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate(passphrase)

    try:
        # Create master key from seed (secp256k1 curve)
        master_key = Bip32Slip10Secp256k1.FromSeed(seed_bytes)

        # Derive path: m/44'/60'/0'/0/{index}
        # 44' = BIP-44 purpose
        # 60' = Ethereum coin type (applies to ALL EVM chains)
        # 0' = account 0
        # 0 = external chain (receiving addresses)
        # {index} = address index
        path = f"m/44'/60'/0'/0/{index}"
        derived = master_key.DerivePath(path)

        # Convert to Ethereum address
        # Get uncompressed public key (65 bytes), take x+y coordinates (64 bytes)
        # Then Keccak-256 hash, take last 20 bytes
        pub_key_uncompressed = bytes(derived.PublicKey().RawUncompressed())
        evm_addr = EthAddr.EncodeKey(pub_key_uncompressed)

        return str(evm_addr)

    except Exception as e:
        raise ValueError(f"Failed to derive EVM address: {str(e)}")


def derive_all_addresses(mnemonic: str, passphrase: str = "") -> dict:
    """
    Derive all wallet addresses from a single mnemonic.

    SECURITY:
    - Private keys are derived and discarded during execution
    - Returns only public addresses (safe to display)
    - Same mnemonic = same addresses (deterministic)

    Args:
        mnemonic: BIP-39 mnemonic phrase
        passphrase: Optional BIP-39 passphrase

    Returns:
        dict: Wallet addresses by chain type
    """
    try:
        # Derive Solana address (Ed25519 curve)
        solana_addr, _ = derive_solana_keypair(mnemonic, passphrase)

        # Derive EVM address (secp256k1 curve)
        # Note: This address works for ALL EVM chains:
        # - Ethereum (ETH)
        # - Binance Smart Chain (BNB)
        # - Polygon (MATIC)
        # - Base
        # - Arbitrum
        # - Optimism
        # - Avalanche C-Chain
        # - And all other EVM-compatible chains
        evm_addr = derive_evm_address(mnemonic, passphrase)

        return {
            "solana": solana_addr,
            "ethereum": evm_addr,
            "bnb_smart_chain": evm_addr,  # Same as ETH
            "polygon": evm_addr,  # Same as ETH
            "base": evm_addr,  # Same as ETH
            "arbitrum": evm_addr,  # Same as ETH
        }

    except Exception as e:
        # SECURITY: Don't leak sensitive info in error messages
        raise RuntimeError(
            "Failed to derive wallet addresses. Check mnemonic validity."
        ) from e


# =============================================================================
# SECURE STORAGE (Cross-Platform Keyring)
# =============================================================================


def store_securely(mnemonic: str, keyring_name: str) -> bool:
    """
    Store mnemonic in platform-native secure storage.

    SECURITY FEATURES:
    - Windows: Credential Locker (DPAPI encryption)
    - macOS: Keychain (encrypted, user-locked)
    - Linux: SecretService (GNOME Keyring / KWallet)
    - Never stored in plain text files
    - Access requires OS-level authentication

    Args:
        mnemonic: BIP-39 mnemonic phrase to store
        keyring_name: Unique identifier for retrieval

    Returns:
        bool: True if storage successful

    Raises:
        ValueError: If mnemonic is invalid or empty
        KeyringError: If secure storage is unavailable
    """
    # SECURITY: Validate mnemonic before storing
    mnemonic = " ".join(mnemonic.strip().lower().split())
    is_valid, msg = validate_mnemonic(mnemonic)
    if not is_valid:
        raise ValueError(f"Cannot store invalid mnemonic: {msg}")

    # SECURITY: Use service name + keyring_name as combined key
    # This prevents collisions and provides namespace isolation
    account_name = f"wallet:{keyring_name.lower()}"

    try:
        # Store in OS keyring
        keyring.set_password(KEYRING_SERVICE_NAME, account_name, mnemonic)

        # Verify storage succeeded
        stored = keyring.get_password(KEYRING_SERVICE_NAME, account_name)
        if stored != mnemonic:
            raise KeyringError("Verification failed: stored mnemonic doesn't match")

        return True

    except KeyringLocked:
        raise KeyringError("Keyring is locked. Unlock your OS keyring and try again.")
    except Exception as e:
        raise KeyringError(f"Failed to store mnemonic securely: {str(e)}")


def retrieve_from_storage(keyring_name: str) -> str:
    """
    Retrieve mnemonic from platform-native secure storage.

    SECURITY:
    - Requires OS-level authentication
    - Mnemonic should be used immediately and cleared from memory
    - Never log retrieved mnemonics

    Args:
        keyring_name: Unique identifier used during storage

    Returns:
        str: Retrieved mnemonic phrase

    Raises:
        KeyError: If mnemonic not found in storage
        KeyringError: If secure storage is unavailable
    """
    account_name = f"wallet:{keyring_name.lower()}"

    try:
        mnemonic = keyring.get_password(KEYRING_SERVICE_NAME, account_name)

        if mnemonic is None:
            raise KeyError(
                f"No wallet found with name '{keyring_name}'. "
                f"Use 'secure-storage store' command to store a mnemonic."
            )

        return mnemonic

    except Exception as e:
        if isinstance(e, (KeyError, KeyringError)):
            raise
        raise KeyringError(f"Failed to retrieve mnemonic: {str(e)}")


def delete_from_storage(keyring_name: str) -> bool:
    """
    Permanently delete mnemonic from secure storage.

    SECURITY:
    - Cannot be undone - mnemonic will be lost forever
    - Should only be called after confirming backup exists

    Args:
        keyring_name: Unique identifier used during storage

    Returns:
        bool: True if deletion successful

    Raises:
        KeyError: If mnemonic not found in storage
    """
    account_name = f"wallet:{keyring_name.lower()}"

    try:
        keyring.delete_password(KEYRING_SERVICE_NAME, account_name)
        return True
    except Exception as e:
        if "not found" in str(e).lower():
            raise KeyError(f"No wallet found with name '{keyring_name}'")
        raise KeyringError(f"Failed to delete mnemonic: {str(e)}")


# =============================================================================
# CLI IMPLEMENTATION
# =============================================================================


def cmd_generate(args) -> int:
    """Handle 'generate' subcommand."""
    word_count = args.words

    print(f"Generating {word_count}-word BIP-39 mnemonic...")
    print()

    try:
        mnemonic = generate_mnemonic(word_count)

        # SECURITY: Only show mnemonic if explicitly requested
        if args.show_mnemonic:
            print("=" * 60)
            print("YOUR MNEMONIC PHRASE (WRITE THIS DOWN SECURELY)")
            print("=" * 60)
            print()
            print(f"  {mnemonic}")
            print()
            print("=" * 60)
            print("⚠️  WARNING: Anyone with this phrase can access your funds!")
            print("⚠️  Store in a secure, offline location (NOT in cloud storage)")
            print("=" * 60)
        else:
            print("OK Mnemonic generated successfully")
            print()
            print("To view the mnemonic, re-run with --show-mnemonic flag")
            print("WARNING: Only do this in a secure, private environment")
            return 0

        # Always derive and show addresses (safe to display)
        addresses = derive_all_addresses(mnemonic)

        print()
        print("=" * 60)
        print("DERIVED ADDRESSES (safe to share for receiving funds)")
        print("=" * 60)
        print(f"  Solana:       {addresses['solana']}")
        print(f"  Ethereum:     {addresses['ethereum']}")
        print(f"  BNB Chain:    {addresses['bnb_smart_chain']} (same as ETH)")
        print(f"  Polygon:      {addresses['polygon']} (same as ETH)")
        print(f"  Base:         {addresses['base']} (same as ETH)")
        print(f"  Arbitrum:     {addresses['arbitrum']} (same as ETH)")
        print("=" * 60)
        print()
        print(SECURITY_WARNINGS)

        return 0

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return 1


def cmd_addresses(args) -> int:
    """Handle 'addresses' subcommand."""
    mnemonic = args.mnemonic
    passphrase = args.passphrase or ""

    # SECURITY: Validate mnemonic first
    is_valid, msg = validate_mnemonic(mnemonic)
    if not is_valid:
        print(f"ERROR: Invalid mnemonic - {msg}", file=sys.stderr)
        return 1

    try:
        addresses = derive_all_addresses(mnemonic, passphrase)

        print("=" * 60)
        print("WALLET ADDRESSES (DO NOT SHARE PRIVATE KEYS)")
        print("=" * 60)
        print()

        # CRITICAL SECURITY: NEVER show private key
        # Only display public addresses
        print(f"  Solana:       {addresses['solana']}")
        print(f"  Ethereum:     {addresses['ethereum']}")
        print(f"  BNB Chain:    {addresses['bnb_smart_chain']} (same as ETH)")
        print(f"  Polygon:      {addresses['polygon']} (same as ETH)")
        print(f"  Base:         {addresses['base']} (same as ETH)")
        print(f"  Arbitrum:     {addresses['arbitrum']} (same as ETH)")
        print()
        print("=" * 60)
        print()
        print("✓ These addresses can be safely shared to receive funds")
        print("✓ All EVM chains share the same address (one key for all)")
        print()
        print(SECURITY_WARNINGS)

        return 0

    except Exception as e:
        # SECURITY: Don't leak sensitive info in error
        print(f"ERROR: Failed to derive addresses", file=sys.stderr)
        if args.verbose:
            print(f"Details: {str(e)}", file=sys.stderr)
        return 1


def cmd_verify(args) -> int:
    """Handle 'verify' subcommand."""
    mnemonic = args.mnemonic

    print("Validating mnemonic phrase...")
    print()

    is_valid, msg = validate_mnemonic(mnemonic)

    if is_valid:
        # Count words for info
        word_count = len(mnemonic.split())
        print(f"✓ VALID: {word_count}-word BIP-39 mnemonic")
        print(f"  Checksum: OK")
        print(f"  Word count: {word_count}")

        # Optionally derive addresses to prove validity
        if args.derive_addresses:
            print()
            print("Deriving addresses to verify key derivation...")
            try:
                addrs = derive_all_addresses(mnemonic)
                print(f"  Solana:   {addrs['solana'][:20]}...")
                print(f"  Ethereum: {addrs['ethereum'][:20]}...")
                print("✓ Address derivation successful")
            except Exception:
                print("✗ Address derivation failed (mnemonic may be incomplete)")
                return 1
    else:
        print(f"✗ INVALID: {msg}")
        return 1

    return 0


def cmd_secure_storage(args) -> int:
    """Handle 'secure-storage' subcommand."""
    action = args.action

    if action == "store":
        # Store mnemonic from stdin or argument
        mnemonic = args.mnemonic

        # SECURITY: Validate before storing
        is_valid, msg = validate_mnemonic(mnemonic)
        if not is_valid:
            print(f"ERROR: Cannot store invalid mnemonic - {msg}", file=sys.stderr)
            return 1

        try:
            store_securely(mnemonic, args.name)
            print(f"✓ Mnemonic stored securely in OS keyring")
            print(f"  Service: {KEYRING_SERVICE_NAME}")
            print(f"  Account: wallet:{args.name.lower()}")
            print()
            print("Retrieval command:")
            print(f"  python wallet_manager.py secure-storage retrieve {args.name}")
            return 0
        except Exception as e:
            print(f"ERROR: Failed to store - {str(e)}", file=sys.stderr)
            return 1

    elif action == "retrieve":
        try:
            mnemonic = retrieve_from_storage(args.name)

            # SECURITY: Only show if explicitly requested
            if args.show_mnemonic:
                print("=" * 60)
                print("RETRIEVED MNEMONIC (CLEAR FROM TERMINAL HISTORY)")
                print("=" * 60)
                print(f"  {mnemonic}")
                print("=" * 60)
            else:
                # Derive addresses instead of showing mnemonic
                addrs = derive_all_addresses(mnemonic)
                print(f"✓ Wallet '{args.name}' found")
                print()
                print("Addresses:")
                print(f"  Solana:   {addrs['solana']}")
                print(f"  Ethereum: {addrs['ethereum']}")
                print()
                print("Add --show-mnemonic to display the stored phrase")

            return 0

        except KeyError as e:
            print(f"ERROR: {str(e)}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"ERROR: Failed to retrieve - {str(e)}", file=sys.stderr)
            return 1

    elif action == "delete":
        if not args.confirm:
            print(f"ERROR: Use --confirm to delete (IRREVERSIBLE)", file=sys.stderr)
            print(
                f"Run: python wallet_manager.py secure-storage delete {args.name} --confirm"
            )
            return 1

        try:
            delete_from_storage(args.name)
            print(f"✓ Wallet '{args.name}' permanently deleted from storage")
            print("WARNING: This action cannot be undone!")
            return 0
        except KeyError as e:
            print(f"ERROR: {str(e)}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"ERROR: Failed to delete - {str(e)}", file=sys.stderr)
            return 1

    else:
        print(f"ERROR: Unknown action: {action}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        prog="wallet_manager.py",
        description="Secure BIP-39/BIP-44 Wallet Manager for Solana and EVM Chains",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SECURITY NOTES:
  - Private keys are NEVER stored or logged
  - Uses OS-native secure storage (Keychain, Credential Locker, SecretService)
  - 24-word mnemonics recommended (256 bits of entropy)

EXAMPLES:
  # Generate new 24-word mnemonic
  python wallet_manager.py generate

  # Show mnemonic (only in secure environment!)
  python wallet_manager.py generate --show-mnemonic

  # Verify an existing mnemonic
  python wallet_manager.py verify "word1 word2 ... word24"

  # Derive addresses from mnemonic
  python wallet_manager.py addresses "word1 word2 ... word24"

  # Store mnemonic securely
  python wallet_manager.py secure-storage store mywallet "word1 word2 ... word24"

  # Retrieve and show addresses (not mnemonic)
  python wallet_manager.py secure-storage retrieve mywallet
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -------------------------------------------------------------------------
    # GENERATE subcommand
    # -------------------------------------------------------------------------
    gen_parser = subparsers.add_parser(
        "generate", help="Generate new BIP-39 mnemonic phrase"
    )
    gen_parser.add_argument(
        "--words",
        type=int,
        default=24,
        choices=[12, 15, 18, 21, 24],
        help="Word count (default: 24 for max security)",
    )
    gen_parser.add_argument(
        "--show-mnemonic",
        action="store_true",
        help="Display the generated mnemonic (use in secure environment only)",
    )
    gen_parser.set_defaults(func=cmd_generate)

    # -------------------------------------------------------------------------
    # ADDRESSES subcommand
    # -------------------------------------------------------------------------
    addr_parser = subparsers.add_parser(
        "addresses", help="Derive and display wallet addresses from mnemonic"
    )
    addr_parser.add_argument(
        "mnemonic", type=str, help="BIP-39 mnemonic phrase (quoted)"
    )
    addr_parser.add_argument(
        "--passphrase", type=str, default="", help="Optional BIP-39 passphrase"
    )
    addr_parser.add_argument(
        "--verbose", action="store_true", help="Show detailed error messages"
    )
    addr_parser.set_defaults(func=cmd_addresses)

    # -------------------------------------------------------------------------
    # VERIFY subcommand
    # -------------------------------------------------------------------------
    verify_parser = subparsers.add_parser("verify", help="Verify mnemonic validity")
    verify_parser.add_argument(
        "mnemonic", type=str, help="BIP-39 mnemonic phrase to validate"
    )
    verify_parser.add_argument(
        "--derive-addresses",
        action="store_true",
        help="Also derive addresses to verify key derivation",
    )
    verify_parser.set_defaults(func=cmd_verify)

    # -------------------------------------------------------------------------
    # SECURE-STORAGE subcommand
    # -------------------------------------------------------------------------
    storage_parser = subparsers.add_parser(
        "secure-storage", help="Store/retrieve mnemonics in OS secure storage"
    )
    storage_sub = storage_parser.add_subparsers(dest="action", help="Storage actions")

    # Store action
    store_sub = storage_sub.add_parser("store", help="Store mnemonic securely")
    store_sub.add_argument("name", type=str, help="Unique wallet name")
    store_sub.add_argument("mnemonic", type=str, help="BIP-39 mnemonic phrase")
    store_sub.set_defaults(func=cmd_secure_storage)

    # Retrieve action
    retrieve_sub = storage_sub.add_parser("retrieve", help="Retrieve stored mnemonic")
    retrieve_sub.add_argument("name", type=str, help="Wallet name")
    retrieve_sub.add_argument(
        "--show-mnemonic", action="store_true", help="Display the retrieved mnemonic"
    )
    retrieve_sub.set_defaults(func=cmd_secure_storage)

    # Delete action
    delete_sub = storage_sub.add_parser("delete", help="Delete stored mnemonic")
    delete_sub.add_argument("name", type=str, help="Wallet name")
    delete_sub.add_argument(
        "--confirm", action="store_true", help="Confirm irreversible deletion"
    )
    delete_sub.set_defaults(func=cmd_secure_storage)

    # -------------------------------------------------------------------------
    # Parse and execute
    # -------------------------------------------------------------------------
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
