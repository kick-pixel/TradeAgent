"""
Wallet Management Module

Handles mnemonic-based wallet derivation for Solana.
Private keys are derived on-demand and never stored.
"""

import os
import hashlib
from typing import Optional, Tuple
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
load_dotenv()

from bip_utils import (
    Bip39SeedGenerator,
    Bip39MnemonicValidator,
    Bip44,
    Bip44Coins,
    Bip44Changes,
)


class WalletManager:
    """
    Secure wallet management using BIP-39 mnemonic.
    
    Security principles:
    - Mnemonic is loaded from environment or secure storage
    - Private keys are derived on-demand and immediately discarded
    - Never log or output private keys
    """
    
    SOLANA_DERIVATION_PATH = "m/44'/501'/0'/0'"
    
    def __init__(self, mnemonic: Optional[str] = None):
        """
        Initialize wallet manager.
        
        Args:
            mnemonic: BIP-39 mnemonic phrase (12 or 24 words).
                     If not provided, reads from MNEMONIC_PHRASE env var.
        """
        self._mnemonic = mnemonic or os.getenv("MNEMONIC_PHRASE", "")
        self._mnemonic = self._mnemonic.strip().strip('"').strip("'")
        
        # Cache derived address (but NOT the private key)
        self._solana_address: Optional[str] = None
        
    @property
    def has_mnemonic(self) -> bool:
        """Check if mnemonic is configured"""
        return bool(self._mnemonic)
    
    def validate_mnemonic(self) -> bool:
        """Validate the mnemonic phrase"""
        if not self._mnemonic:
            return False
        try:
            Bip39MnemonicValidator().Validate(self._mnemonic)
            return True
        except Exception:
            return False
    
    def derive_solana_keypair(self) -> Tuple[str, str]:
        """
        Derive Solana address and private key from mnemonic.
        
        Uses Phantom-compatible derivation path: m/44'/501'/0'/0'
        
        Returns:
            Tuple of (address, private_key_base58)
            
        Note:
            Private key should be used immediately and not stored.
        """
        if not self._mnemonic:
            raise ValueError("No mnemonic configured. Set MNEMONIC_PHRASE in .env")
        
        # Validate mnemonic
        Bip39MnemonicValidator().Validate(self._mnemonic)
        
        # Generate seed
        seed_bytes = Bip39SeedGenerator(self._mnemonic).Generate()
        
        # Phantom uses SLIP-0010 Ed25519 derivation
        # Path: m/44'/501'/0'/0' (all hardened indexes)
        from bip_utils import Bip32Slip10Ed25519
        from solders.keypair import Keypair
        
        bip32_ctx = Bip32Slip10Ed25519.FromSeed(seed_bytes)
        
        # Derive path m/44'/501'/0'/0'
        derived = (bip32_ctx
                   .ChildKey(0x80000000 + 44)   # Purpose
                   .ChildKey(0x80000000 + 501)  # Coin (Solana)
                   .ChildKey(0x80000000 + 0)    # Account
                   .ChildKey(0x80000000 + 0))   # Index
        
        # Get private key bytes
        private_key_bytes = derived.PrivateKey().Raw().ToBytes()
        
        # Create Solana keypair
        keypair = Keypair.from_seed(private_key_bytes[:32])
        
        # Get address
        address = str(keypair.pubkey())
        
        # Encode private key for signing script
        import base58
        private_key_b58 = base58.b58encode(private_key_bytes).decode('utf-8')
        
        # Cache address
        self._solana_address = address
        
        return address, private_key_b58
    
    def get_solana_address(self) -> str:
        """Get Solana address (cached, no private key derivation)"""
        if self._solana_address:
            return self._solana_address
        
        address, _ = self.derive_solana_keypair()
        return address
    
    def sign_and_send_swap(
        self,
        order_id: str,
        from_chain: str,
        from_contract: str,
        from_symbol: str,
        from_amount: str,
        to_chain: str,
        to_contract: str,
        to_symbol: str,
        from_address: str,
        to_address: str,
        market: str,
        protocol: str,
        slippage: str,
    ) -> dict:
        """
        Execute a complete swap: makeOrder → sign → send.
        
        This is the only method that handles private keys.
        The key is used in memory and discarded immediately.
        """
        import subprocess
        import sys
        import json
        
        if not self.has_mnemonic:
            return {
                "error": "No mnemonic configured. Set MNEMONIC_PHRASE in .env"
            }
        
        # Derive keypair (private key only lives in this scope)
        try:
            _, private_key_sol = self.derive_solana_keypair()
        except Exception as e:
            return {"error": f"Failed to derive keypair: {str(e)}"}
        
        # Path to signing script
        script_path = Path(__file__).parent.parent / "skills" / "bitget-wallet-skill" / "scripts" / "order_make_sign_send.py"
        
        # Build command
        cmd = [
            sys.executable,
            str(script_path),
            "--private-key-sol", private_key_sol,
            "--from-address", from_address,
            "--to-address", to_address,
            "--order-id", order_id,
            "--from-chain", from_chain,
            "--from-contract", from_contract,
            "--from-symbol", from_symbol,
            "--to-chain", to_chain,
            "--to-contract", to_contract or "",
            "--to-symbol", to_symbol,
            "--from-amount", str(from_amount),
            "--slippage", str(slippage),
            "--market", market,
            "--protocol", protocol,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Clear private key from memory immediately
            private_key_sol = None
            
            if result.returncode != 0:
                return {
                    "error": result.stderr or "Unknown error during swap execution"
                }
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            private_key_sol = None
            return {"error": "Swap execution timed out"}
        except Exception as e:
            private_key_sol = None
            return {"error": str(e)}
        finally:
            # Ensure private key is cleared
            private_key_sol = None


# Global wallet manager instance
_wallet_manager: Optional[WalletManager] = None


def get_wallet_manager() -> WalletManager:
    """Get or create wallet manager instance"""
    global _wallet_manager
    if _wallet_manager is None:
        _wallet_manager = WalletManager()
    return _wallet_manager


def get_solana_address() -> Optional[str]:
    """Get configured Solana address, or None if not configured"""
    try:
        wm = get_wallet_manager()
        if wm.has_mnemonic:
            return wm.get_solana_address()
    except Exception:
        pass
    return None
