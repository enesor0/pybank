import os
import tempfile
import unittest
from pathlib import Path

from pybank.bootstrap import build_application
from pybank.domain.errors import DomainError
from pybank.domain.models import CardKind, Iban


class BankingIntegrationTests(unittest.TestCase):
    def setUp(self):
        descriptor, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(descriptor)
        self.database = Path(path)
        self.application = build_application(self.database)
        self.alice = self.application.authentication.register("Alice Kaya", "alice@example.com", "Guvenli123")
        self.bob = self.application.authentication.register("Bob Demir", "bob@example.com", "Guvenli123")
        self.alice_account = self.application.banking.open_account(self.alice.id)
        self.bob_account = self.application.banking.open_account(self.bob.id)

    def tearDown(self):
        self.application.banking.repository.connection.close()
        self.database.unlink(missing_ok=True)

    def test_iban_generation_is_valid(self):
        self.assertEqual(Iban.generate(1).value, self.alice_account.iban.value)

    def test_transfer_is_atomic_and_creates_two_ledger_entries(self):
        bank = self.application.banking
        bank.deposit(self.alice.id, self.alice_account.id, "2500.50", "İlk bakiye")
        bank.transfer(self.alice.id, self.alice_account.id, self.bob_account.iban.display, "500.25", "Paylaşım")
        alice_dashboard = bank.dashboard(self.alice.id, self.alice_account.id)
        bob_dashboard = bank.dashboard(self.bob.id, self.bob_account.id)
        self.assertEqual(str(alice_dashboard.account.balance), "2000.25")
        self.assertEqual(str(bob_dashboard.account.balance), "500.25")
        self.assertEqual(len(alice_dashboard.transactions), 2)
        self.assertEqual(len(bob_dashboard.transactions), 1)

    def test_turkish_money_format_and_external_iban_transfer(self):
        bank = self.application.banking
        bank.deposit(self.alice.id, self.alice_account.id, "1.250,50")
        external_iban = Iban.generate(999).display
        bank.transfer(self.alice.id, self.alice_account.id, external_iban, "250,25", "EFT")
        dashboard = bank.dashboard(self.alice.id, self.alice_account.id)
        self.assertEqual(dashboard.account.balance, 1000.25)
        self.assertEqual(len(dashboard.transactions), 2)

    def test_insufficient_balance_does_not_change_balance(self):
        with self.assertRaises(DomainError):
            self.application.banking.withdraw(self.alice.id, self.alice_account.id, "1")
        self.assertEqual(self.application.banking.dashboard(self.alice.id).account.balance, 0)

    def test_banka_and_virtual_cards_have_separate_types_and_settings(self):
        bank = self.application.banking
        debit = bank.issue_card(self.alice.id, self.alice_account.id, CardKind.BANKA)
        virtual = bank.issue_card(self.alice.id, self.alice_account.id, CardKind.SANAL)
        credit = bank.issue_card(self.alice.id, self.alice_account.id, CardKind.KREDI)
        self.assertEqual([card.kind for card in bank.cards_for(self.alice.id)], [CardKind.BANKA, CardKind.SANAL, CardKind.KREDI])
        self.assertEqual(credit.credit_limit, 25000)
        bank.toggle_card_freeze(self.alice.id, virtual.id)
        self.assertFalse(debit.is_frozen)
        self.assertTrue(next(card for card in bank.cards_for(self.alice.id) if card.id == virtual.id).is_frozen)
        bank.close_card(self.alice.id, debit.id)
        closed = next(card for card in bank.cards_for(self.alice.id) if card.id == debit.id)
        self.assertTrue(closed.is_closed)
        self.assertTrue(closed.is_frozen)
        self.assertFalse(closed.contactless_enabled)


if __name__ == "__main__":
    unittest.main()
