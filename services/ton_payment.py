"""TON payment integration stubs with safe fallbacks.

The real TON client (tonutils) may not be available in all environments. This
module provides minimal stubs and typed docstrings so the application can run
without blockchain dependencies while keeping a clear upgrade path.
"""
from typing import Optional

# Safe import: tonutils can be missing in the environment
try:
    from tonutils.api import TonapiClient  # type: ignore
    from tonutils.contract import Wallet  # type: ignore
    from tonutils.utils import to_nano  # type: ignore
    _TONUTILS_AVAILABLE = True
except Exception:  # noqa: E722 - silence any import error to keep app functional
    _TONUTILS_AVAILABLE = False

    class TonapiClient:  # minimal stub
        def __init__(self, api_key: str = ""):
            self.api_key = api_key

    class Wallet:  # minimal wallet stub with an address
        def __init__(self, client: Optional["TonapiClient"] = None, address: str = "UQ_FAKE_ADDRESS"):
            self.client = client
            self.address = address

        @classmethod
        def from_mnemonic(cls, client: Optional["TonapiClient"], mnemonic):
            # Real implementation would restore a wallet from mnemonic words.
            # The stub returns a fixed, clearly-fake address.
            return cls(client=client, address="UQ_FAKE_ADDRESS")

    def to_nano(amount_ton: float) -> int:
        """Convert TON to nanoTON with defensive casting."""
        try:
            return int(float(amount_ton) * 1_000_000_000)
        except Exception:
            return 0

from config import TON_API_KEY, TON_WALLET_MNEMONIC


async def confirm_delivery(deal_id: str) -> dict:
    """Simulate releasing funds for a completed deal.

    In a real integration this would call a smart contract method (release).
    """
    if not deal_id:
        raise ValueError("deal_id must be provided")
    return {"status": "funds_released", "deal_id": deal_id}


async def request_refund(deal_id: str) -> dict:
    """Simulate initiating a refund for a disputed deal.

    Real implementations would trigger an arbitration flow.
    """
    if not deal_id:
        raise ValueError("deal_id must be provided")
    return {"status": "refund_requested", "deal_id": deal_id}


class TONPaymentService:
    """High-level helper around TON client/wallet with safe fallbacks."""

    def __init__(self) -> None:
        # Initialize client and wallet, remaining resilient if tonutils/configs
        # are absent or invalid.
        try:
            self.client = TonapiClient(api_key=TON_API_KEY or "")
        except Exception:
            # Never break the app due to client init failures
            self.client = TonapiClient(api_key="")

        try:
            mnemonic = TON_WALLET_MNEMONIC or []
            # Wallet.from_mnemonic expects a list of words
            self.wallet = Wallet.from_mnemonic(client=self.client, mnemonic=mnemonic)
        except Exception:
            # Fallback to a stub wallet with a clearly fake address
            self.wallet = Wallet(client=self.client, address="UQ_FAKE_ADDRESS")

    async def create_escrow_deal(self, buyer_address: str, amount_ton: float, timeout_days: int = 7) -> dict:
        """Create an escrow-like deal by freezing funds (simulated).

        Args:
            buyer_address: The buyer's TON address.
            amount_ton: Transfer amount in TON.
            timeout_days: Escrow timeout window in days.
        """
        # Basic validation with clear error messages
        if not isinstance(buyer_address, str) or not buyer_address:
            raise ValueError("buyer_address must be a non-empty string")
        try:
            amount_ton_num = float(amount_ton)
        except Exception as e:
            raise ValueError("amount_ton must be a number") from e
        if amount_ton_num <= 0:
            raise ValueError("amount_ton must be positive")
        if not isinstance(timeout_days, int) or timeout_days <= 0:
            raise ValueError("timeout_days must be a positive integer")

        amount_nano = to_nano(amount_ton_num)
        # In reality this would be a smart-contract call. Here we return a stub.
        return {
            "deal_id": f"deal_{abs(hash((buyer_address, amount_nano, timeout_days)))%10_000_000}",
            "buyer": buyer_address,
            "seller": getattr(self.wallet, "address", "UQ_FAKE_ADDRESS"),
            "amount_ton": amount_ton_num,
            "amount_nano": amount_nano,
            "status": "frozen",
            "timeout_days": timeout_days,
            "contract_address": getattr(self.wallet, "address", "UQ_FAKE_ADDRESS"),
        }
