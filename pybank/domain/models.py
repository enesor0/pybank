from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from uuid import UUID, uuid4

from .errors import DomainError


CENT = Decimal("0.01")


def money(value: Decimal | str | int | float) -> Decimal:
    """Tüm parasal değerleri iki haneli Decimal olarak normalize eder."""
    try:
        raw_value = str(value).strip().replace("₺", "").replace(" ", "")
        # Türkçe biçim (1.250,50) ve nokta biçimi (1250.50) desteklenir.
        if "," in raw_value and "." in raw_value:
            raw_value = raw_value.replace(".", "").replace(",", ".")
        elif "," in raw_value:
            raw_value = raw_value.replace(",", ".")
        result = Decimal(raw_value).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as error:
        raise DomainError("Geçerli bir tutar girin.") from error
    if result <= 0:
        raise DomainError("Tutar sıfırdan büyük olmalıdır.")
    return result


def format_money(value: Decimal) -> str:
    return f"₺{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


@dataclass(frozen=True)
class Iban:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.replace(" ", "").upper()
        if len(normalized) != 26 or not normalized.startswith("TR") or not normalized[2:].isdigit():
            raise DomainError("Geçerli bir Türkiye IBAN'ı girin.")
        numeric = normalized[4:] + "2927" + normalized[2:4]
        if int(numeric) % 97 != 1:
            raise DomainError("IBAN doğrulama kontrolünden geçemedi.")
        object.__setattr__(self, "value", normalized)

    @classmethod
    def generate(cls, sequence: int) -> "Iban":
        bban = f"0001000000000000{sequence:06d}"
        check_digits = 98 - int(bban + "292700") % 97
        return cls(f"TR{check_digits:02d}{bban}")

    @property
    def display(self) -> str:
        return " ".join(self.value[index:index + 4] for index in range(0, 26, 4))


class AccountKind(str, Enum):
    VADESIZ = "Vadesiz Hesap"
    BIRIKIM = "Birikim Hesabı"


class CardKind(str, Enum):
    BANKA = "Banka Kartı"
    SANAL = "Sanal Kart"
    KREDI = "Kredi Kartı"


class EntryType(str, Enum):
    DEPOSIT = "Para Yatırma"
    WITHDRAWAL = "Para Çekme"
    TRANSFER_OUT = "Gönderilen Transfer"
    TRANSFER_IN = "Gelen Transfer"
    BILL_PAYMENT = "Fatura Ödemesi"


@dataclass
class Account:
    id: UUID
    customer_id: UUID
    iban: Iban
    kind: AccountKind
    balance: Decimal
    opened_at: datetime
    is_active: bool = True

    def ensure_operable(self) -> None:
        if not self.is_active:
            raise DomainError("Bu hesap işlem yapmaya kapalıdır.")

    def credit(self, amount: Decimal | str | int | float) -> Decimal:
        self.ensure_operable()
        amount = money(amount)
        self.balance += amount
        return amount

    def debit(self, amount: Decimal | str | int | float) -> Decimal:
        self.ensure_operable()
        amount = money(amount)
        if self.balance < amount:
            raise DomainError("Yetersiz bakiye.")
        self.balance -= amount
        return amount


@dataclass
class Card:
    """Yerel uygulamada yalnızca maskeli bilgisi gösterilen sanal banka kartı."""
    id: UUID
    customer_id: UUID
    account_id: UUID
    kind: CardKind
    label: str
    last_four: str
    expiry: str
    is_frozen: bool = False
    contactless_enabled: bool = True
    credit_limit: Decimal = Decimal("0.00")
    debt: Decimal = Decimal("0.00")
    is_closed: bool = False

    def toggle_freeze(self) -> None:
        if self.is_closed:
            raise DomainError("Kapatılmış kartta işlem yapılamaz.")
        self.is_frozen = not self.is_frozen

    def toggle_contactless(self) -> None:
        if self.is_closed:
            raise DomainError("Kapatılmış kartta işlem yapılamaz.")
        self.contactless_enabled = not self.contactless_enabled

    def close(self) -> None:
        if self.is_closed:
            raise DomainError("Bu kart için kapatma talimatı zaten verilmiş.")
        self.is_closed = True
        self.is_frozen = True
        self.contactless_enabled = False

    @property
    def available_credit(self) -> Decimal:
        return self.credit_limit - self.debt


@dataclass(frozen=True)
class LedgerEntry:
    id: UUID
    account_id: UUID
    entry_type: EntryType
    amount: Decimal
    description: str
    created_at: datetime
    transfer_id: UUID | None = None
    counterparty_iban: str | None = None

    @classmethod
    def create(cls, account_id: UUID, entry_type: EntryType, amount: Decimal,
               description: str = "", transfer_id: UUID | None = None,
               counterparty_iban: str | None = None) -> "LedgerEntry":
        return cls(uuid4(), account_id, entry_type, money(amount), description.strip()[:140],
                   datetime.now(timezone.utc), transfer_id, counterparty_iban)
