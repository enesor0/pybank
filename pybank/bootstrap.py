from pathlib import Path

from pybank.application.services import AuthenticationService, BankingService
from pybank.infrastructure.sqlite_repositories import SqliteRepository


class Application:
    def __init__(self, database_path: Path) -> None:
        self.repository = SqliteRepository(database_path)
        self.authentication = AuthenticationService(self.repository)
        self.banking = BankingService(self.repository)

    def close(self) -> None:
        self.repository.close()


def build_application(database_path: Path) -> Application:
    return Application(database_path)
