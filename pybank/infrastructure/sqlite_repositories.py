from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from pybank.application.ports import UserCredential
from pybank.domain.models import Account, AccountKind, Card, CardKind, EntryType, Iban, LedgerEntry


class SqliteRepository:
    """SQLite adapter: şema, transaction ve tüm kalıcılık işlemleri burada kalır."""

    def __init__(self, database_path: Path) -> None:
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, full_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, password_salt TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES users(id), iban TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL, balance_cents INTEGER NOT NULL CHECK(balance_cents >= 0),
            opened_at TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS ledger_entries (
            id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id), entry_type TEXT NOT NULL,
            amount_cents INTEGER NOT NULL CHECK(amount_cents > 0), description TEXT NOT NULL,
            created_at TEXT NOT NULL, transfer_id TEXT, counterparty_iban TEXT
        );
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES users(id),
            account_id TEXT NOT NULL REFERENCES accounts(id), label TEXT NOT NULL,
            card_type TEXT NOT NULL DEFAULT 'Banka Kartı', last_four TEXT NOT NULL, expiry TEXT NOT NULL, is_frozen INTEGER NOT NULL DEFAULT 0,
            contactless_enabled INTEGER NOT NULL DEFAULT 1, credit_limit_cents INTEGER NOT NULL DEFAULT 0,
            debt_cents INTEGER NOT NULL DEFAULT 0, is_closed INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_accounts_customer ON accounts(customer_id);
        CREATE INDEX IF NOT EXISTS idx_entries_account_date ON ledger_entries(account_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_cards_customer ON cards(customer_id);
        """)
        # Eski veritabanlarına kart türü alanını güvenle ekler.
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(cards)")}
        if "card_type" not in columns:
            self.connection.execute("ALTER TABLE cards ADD COLUMN card_type TEXT NOT NULL DEFAULT 'Banka Kartı'")
        if "credit_limit_cents" not in columns:
            self.connection.execute("ALTER TABLE cards ADD COLUMN credit_limit_cents INTEGER NOT NULL DEFAULT 0")
        if "debt_cents" not in columns:
            self.connection.execute("ALTER TABLE cards ADD COLUMN debt_cents INTEGER NOT NULL DEFAULT 0")
        if "is_closed" not in columns:
            self.connection.execute("ALTER TABLE cards ADD COLUMN is_closed INTEGER NOT NULL DEFAULT 0")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def atomic(self):
        try:
            self.connection.execute("BEGIN")
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def find_by_email(self, email: str) -> UserCredential | None:
        row = self.connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return self._user(row) if row else None

    def create(self, full_name: str, email: str, password_hash: str, password_salt: str) -> UserCredential:
        user = UserCredential(uuid4(), full_name, email, password_hash, password_salt)
        self.connection.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                                (str(user.id), full_name, email, password_hash, password_salt, datetime.now().isoformat()))
        self.connection.commit()
        return user

    def next_iban_sequence(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]) + 1

    def add_account(self, account: Account) -> None:
        self.connection.execute("INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (str(account.id), str(account.customer_id), account.iban.value, account.kind.value,
                                 self._to_cents(account.balance), account.opened_at.isoformat(), int(account.is_active)))

    def get_account(self, account_id: UUID) -> Account | None:
        row = self.connection.execute("SELECT * FROM accounts WHERE id = ?", (str(account_id),)).fetchone()
        return self._account(row) if row else None

    def get_account_by_iban(self, iban: str) -> Account | None:
        row = self.connection.execute("SELECT * FROM accounts WHERE iban = ?", (iban,)).fetchone()
        return self._account(row) if row else None

    def list_accounts(self, customer_id: UUID) -> list[Account]:
        rows = self.connection.execute("SELECT * FROM accounts WHERE customer_id = ? ORDER BY opened_at", (str(customer_id),)).fetchall()
        return [self._account(row) for row in rows]

    def update_account(self, account: Account) -> None:
        self.connection.execute("UPDATE accounts SET balance_cents = ?, is_active = ? WHERE id = ?",
                                (self._to_cents(account.balance), int(account.is_active), str(account.id)))

    def add_ledger_entry(self, entry: LedgerEntry) -> None:
        self.connection.execute("INSERT INTO ledger_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (str(entry.id), str(entry.account_id), entry.entry_type.value, self._to_cents(entry.amount),
                                 entry.description, entry.created_at.isoformat(),
                                 str(entry.transfer_id) if entry.transfer_id else None, entry.counterparty_iban))

    def list_ledger_entries(self, account_id: UUID, limit: int = 100) -> list[LedgerEntry]:
        rows = self.connection.execute("SELECT * FROM ledger_entries WHERE account_id = ? ORDER BY created_at DESC LIMIT ?",
                                       (str(account_id), limit)).fetchall()
        return [LedgerEntry(UUID(row["id"]), UUID(row["account_id"]), EntryType(row["entry_type"]),
                            Decimal(row["amount_cents"]) / 100, row["description"],
                            datetime.fromisoformat(row["created_at"]), UUID(row["transfer_id"]) if row["transfer_id"] else None,
                            row["counterparty_iban"]) for row in rows]

    def add_card(self, card: Card) -> None:
        self.connection.execute("""
                                INSERT INTO cards
                                (id, customer_id, account_id, label, card_type, last_four, expiry, is_frozen, contactless_enabled, credit_limit_cents, debt_cents, is_closed)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (str(card.id), str(card.customer_id), str(card.account_id), card.label, card.kind.value,
                                 card.last_four, card.expiry, int(card.is_frozen), int(card.contactless_enabled),
                                 self._to_cents(card.credit_limit), self._to_cents(card.debt), int(card.is_closed)))

    def get_card(self, card_id: UUID) -> Card | None:
        row = self.connection.execute("SELECT * FROM cards WHERE id = ?", (str(card_id),)).fetchone()
        return self._card(row) if row else None

    def list_cards(self, customer_id: UUID) -> list[Card]:
        rows = self.connection.execute("SELECT * FROM cards WHERE customer_id = ? ORDER BY rowid", (str(customer_id),)).fetchall()
        return [self._card(row) for row in rows]

    def update_card(self, card: Card) -> None:
        self.connection.execute("UPDATE cards SET is_frozen = ?, contactless_enabled = ?, is_closed = ? WHERE id = ?",
                                (int(card.is_frozen), int(card.contactless_enabled), int(card.is_closed), str(card.id)))

    @staticmethod
    def _to_cents(amount: Decimal) -> int:
        return int(amount * 100)

    @staticmethod
    def _user(row: sqlite3.Row) -> UserCredential:
        return UserCredential(UUID(row["id"]), row["full_name"], row["email"], row["password_hash"], row["password_salt"])

    @staticmethod
    def _account(row: sqlite3.Row) -> Account:
        return Account(UUID(row["id"]), UUID(row["customer_id"]), Iban(row["iban"]), AccountKind(row["kind"]),
                       Decimal(row["balance_cents"]) / 100, datetime.fromisoformat(row["opened_at"]), bool(row["is_active"]))

    @staticmethod
    def _card(row: sqlite3.Row) -> Card:
        return Card(UUID(row["id"]), UUID(row["customer_id"]), UUID(row["account_id"]), CardKind(row["card_type"]),
                    row["label"], row["last_four"], row["expiry"], bool(row["is_frozen"]), bool(row["contactless_enabled"]),
                    Decimal(row["credit_limit_cents"]) / 100, Decimal(row["debt_cents"]) / 100, bool(row["is_closed"]))
