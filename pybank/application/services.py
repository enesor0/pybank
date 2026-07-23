from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from pybank.domain.errors import DomainError
from pybank.domain.models import Account, AccountKind, Card, CardKind, EntryType, Iban, LedgerEntry, money

from .ports import BankRepository, UserCredential, UserRepository


class ApplicationError(ValueError):
    """Kullanıcıya gösterilebilecek uygulama seviyesi hata."""


class PasswordHasher:
    ITERATIONS = 310_000

    @classmethod
    def hash(cls, password: str, salt: str | None = None) -> tuple[str, str]:
        salt = salt or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), cls.ITERATIONS)
        return digest.hex(), salt

    @classmethod
    def verify(cls, password: str, stored_hash: str, salt: str) -> bool:
        candidate, _ = cls.hash(password, salt)
        return hmac.compare_digest(candidate, stored_hash)


class AuthenticationService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def register(self, full_name: str, email: str, password: str) -> UserCredential:
        full_name, email = full_name.strip(), email.strip().lower()
        if len(full_name) < 2:
            raise ApplicationError("Ad soyad en az 2 karakter olmalıdır.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ApplicationError("Geçerli bir e-posta adresi girin.")
        if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            raise ApplicationError("Parola en az 8 karakter; harf ve rakam içermelidir.")
        if self.users.find_by_email(email):
            raise ApplicationError("Bu e-posta ile kayıtlı bir kullanıcı var.")
        password_hash, salt = PasswordHasher.hash(password)
        return self.users.create(full_name, email, password_hash, salt)

    def login(self, email: str, password: str) -> UserCredential:
        user = self.users.find_by_email(email.strip().lower())
        if not user or not PasswordHasher.verify(password, user.password_hash, user.password_salt):
            raise ApplicationError("E-posta veya parola hatalı.")
        return user


@dataclass(frozen=True)
class Dashboard:
    account: Account
    accounts: list[Account]
    transactions: list[LedgerEntry]


class BankingService:
    def __init__(self, repository: BankRepository) -> None:
        self.repository = repository

    def open_account(self, customer_id: UUID, kind: AccountKind = AccountKind.VADESIZ) -> Account:
        with self.repository.atomic():
            account = Account(uuid4(), customer_id, Iban.generate(self.repository.next_iban_sequence()), kind,
                              Decimal("0.00"), datetime.now(timezone.utc))
            self.repository.add_account(account)
            return account

    def accounts_for(self, customer_id: UUID) -> list[Account]:
        return self.repository.list_accounts(customer_id)

    def dashboard(self, customer_id: UUID, account_id: UUID | None = None) -> Dashboard:
        accounts = self.repository.list_accounts(customer_id)
        if not accounts:
            account = self.open_account(customer_id)
            accounts = [account]
        account = next((item for item in accounts if item.id == account_id), accounts[0])
        if account.customer_id != customer_id:
            raise ApplicationError("Bu hesaba erişim yetkiniz yok.")
        return Dashboard(account, accounts, self.repository.list_ledger_entries(account.id))

    def deposit(self, customer_id: UUID, account_id: UUID, raw_amount: str, description: str = "") -> None:
        with self.repository.atomic():
            account = self._owned_account(customer_id, account_id)
            amount = account.credit(money(raw_amount))
            self.repository.update_account(account)
            self.repository.add_ledger_entry(LedgerEntry.create(account.id, EntryType.DEPOSIT, amount, description))

    def withdraw(self, customer_id: UUID, account_id: UUID, raw_amount: str, description: str = "") -> None:
        with self.repository.atomic():
            account = self._owned_account(customer_id, account_id)
            amount = account.debit(money(raw_amount))
            self.repository.update_account(account)
            self.repository.add_ledger_entry(LedgerEntry.create(account.id, EntryType.WITHDRAWAL, amount, description))

    def pay_bill(self, customer_id: UUID, account_id: UUID, provider: str, subscriber_no: str,
                 raw_amount: str) -> None:
        provider, subscriber_no = provider.strip(), subscriber_no.strip()
        if not provider or not subscriber_no:
            raise ApplicationError("Kurum ve abone numarası zorunludur.")
        with self.repository.atomic():
            account = self._owned_account(customer_id, account_id)
            try:
                amount = account.debit(money(raw_amount))
            except DomainError as error:
                raise ApplicationError(str(error)) from error
            self.repository.update_account(account)
            self.repository.add_ledger_entry(LedgerEntry.create(
                account.id, EntryType.BILL_PAYMENT, amount, f"{provider} • Abone: {subscriber_no}"
            ))

    def issue_card(self, customer_id: UUID, account_id: UUID, kind: CardKind = CardKind.BANKA,
                   label: str = "") -> Card:
        with self.repository.atomic():
            self._owned_account(customer_id, account_id)
            number = len(self.repository.list_cards(customer_id)) + 1
            default_label = {
                CardKind.SANAL: "PyBank Sanal Kart",
                CardKind.KREDI: "PyBank Kredi Kartı",
            }.get(kind, "PyBank Banka Kartı")
            credit_limit = Decimal("25000.00") if kind == CardKind.KREDI else Decimal("0.00")
            card = Card(uuid4(), customer_id, account_id, kind, label.strip()[:24] or default_label,
                        f"{number:04d}", "12/30", credit_limit=credit_limit)
            self.repository.add_card(card)
            return card

    def cards_for(self, customer_id: UUID) -> list[Card]:
        return self.repository.list_cards(customer_id)

    def toggle_card_freeze(self, customer_id: UUID, card_id: UUID) -> Card:
        with self.repository.atomic():
            card = self.repository.get_card(card_id)
            if card is None or card.customer_id != customer_id:
                raise ApplicationError("Bu karta erişim yetkiniz yok.")
            card.toggle_freeze()
            self.repository.update_card(card)
            return card

    def toggle_contactless(self, customer_id: UUID, card_id: UUID) -> Card:
        with self.repository.atomic():
            card = self.repository.get_card(card_id)
            if card is None or card.customer_id != customer_id:
                raise ApplicationError("Bu karta erişim yetkiniz yok.")
            card.toggle_contactless()
            self.repository.update_card(card)
            return card

    def close_card(self, customer_id: UUID, card_id: UUID) -> Card:
        with self.repository.atomic():
            card = self.repository.get_card(card_id)
            if card is None or card.customer_id != customer_id:
                raise ApplicationError("Bu karta erişim yetkiniz yok.")
            try:
                card.close()
            except DomainError as error:
                raise ApplicationError(str(error)) from error
            self.repository.update_card(card)
            return card

    def transfer(self, customer_id: UUID, source_id: UUID, target_iban: str, raw_amount: str,
                 description: str = "") -> None:
        try:
            iban = Iban(target_iban).value
        except DomainError as error:
            raise ApplicationError(str(error)) from error
        with self.repository.atomic():
            source = self._owned_account(customer_id, source_id)
            target = self.repository.get_account_by_iban(iban)
            if target is not None and target.id == source.id:
                raise ApplicationError("Kendi hesabınıza transfer yapamazsınız.")
            try:
                amount = source.debit(money(raw_amount))
                if target is not None:
                    target.credit(amount)
            except DomainError as error:
                raise ApplicationError(str(error)) from error
            self.repository.update_account(source)
            transfer_id = uuid4()
            self.repository.add_ledger_entry(LedgerEntry.create(source.id, EntryType.TRANSFER_OUT, amount, description,
                                                                 transfer_id, iban))
            # Alıcı PyBank içindeyse kayıt iki taraflı oluşur; dış IBAN için giden EFT kaydı tutulur.
            if target is not None:
                self.repository.update_account(target)
                self.repository.add_ledger_entry(LedgerEntry.create(target.id, EntryType.TRANSFER_IN, amount,
                                                                     description or "Gelen transfer", transfer_id, source.iban.value))

    def _owned_account(self, customer_id: UUID, account_id: UUID) -> Account:
        account = self.repository.get_account(account_id)
        if not account or account.customer_id != customer_id:
            raise ApplicationError("Bu hesap için işlem yetkiniz yok.")
        return account
