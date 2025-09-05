# services/ton_payment.py
from typing import Optional

# Безопасные импорты: tonutils может отсутствовать в окружении
try:
    from tonutils.api import TonapiClient  # type: ignore
    from tonutils.contract import Wallet  # type: ignore
    from tonutils.utils import to_nano  # type: ignore
    _TONUTILS_AVAILABLE = True
except Exception:  # noqa: E722 - максимально безопасно гасим любые ошибки импорта
    _TONUTILS_AVAILABLE = False

    class TonapiClient:  # минимальный стаб-класс
        def __init__(self, api_key: str = ""):
            self.api_key = api_key

    class Wallet:  # минимальный стаб с адресом
        def __init__(self, client: Optional[TonapiClient] = None, address: str = "UQ_FAKE_ADDRESS"):
            self.client = client
            self.address = address

        @classmethod
        def from_mnemonic(cls, client: Optional[TonapiClient], mnemonic):
            # В реальности здесь происходит восстановление кошелька.
            # Для стаба вернём фиксированный адрес.
            return cls(client=client, address="UQ_FAKE_ADDRESS")

    def to_nano(amount_ton: float) -> int:
        try:
            return int(float(amount_ton) * 1_000_000_000)
        except Exception:
            return 0

from config import TON_API_KEY, TON_WALLET_MNEMONIC


async def confirm_delivery(deal_id: str):
    # Вызов метода смарт-контракта: release (имитация)
    if not deal_id:
        raise ValueError("deal_id must be provided")
    return {"status": "funds_released", "deal_id": deal_id}


async def request_refund(deal_id: str):
    # Инициирует возврат, требует арбитража (имитация)
    if not deal_id:
        raise ValueError("deal_id must be provided")
    return {"status": "refund_requested", "deal_id": deal_id}


class TONPaymentService:
    def __init__(self):
        # Инициализация клиента и кошелька с учётом отсутствия tonutils/конфигов
        try:
            self.client = TonapiClient(api_key=TON_API_KEY or "")
        except Exception:
            # На всякий случай — никогда не ронять импорт приложения
            self.client = TonapiClient(api_key="")

        try:
            mnemonic = TON_WALLET_MNEMONIC or []
            # Wallet.from_mnemonic ожидает список слов мнемоники
            self.wallet = Wallet.from_mnemonic(client=self.client, mnemonic=mnemonic)
        except Exception:
            # Фоллбек на стаб-кошелёк
            self.wallet = Wallet(client=self.client, address="UQ_FAKE_ADDRESS")

    async def create_escrow_deal(self, buyer_address: str, amount_ton: float, timeout_days: int = 7):
        """
        Создаёт escrow-сделку (упрощённо: просто заморозка средств)
        В реальности — смарт-контракт. Здесь — имитация с безопасной конвертацией TON→nano.
        """
        # Валидация входных данных в самом простом виде
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
        # Здесь должен быть вызов смарт-контракта (депозит/заморозка средств)
        # Пока просто возвращаем имитацию "сделки"
        return {
            "deal_id": f"deal_{abs(hash((buyer_address, amount_nano, timeout_days)))%10_000_000}",
            "buyer": buyer_address,
            "seller": getattr(self.wallet, "address", "UQ_FAKE_ADDRESS"),
            "amount_ton": amount_ton_num,
            "amount_nano": amount_nano,
            "status": "frozen",
            "timeout_days": timeout_days,
            "contract_address": getattr(self.wallet, "address", "UQ_FAKE_ADDRESS"),  # имитация адреса контракта
        }
