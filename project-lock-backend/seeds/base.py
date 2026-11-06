from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class Seeder(ABC):
    """Base class for seeders.

    Each run() must be idempotent: running the seeder twice must not create duplicate rows.
    Use get-or-create checks or upserts keyed on a natural/unique column.
    """

    @abstractmethod
    async def run(self, session: AsyncSession) -> None:
        """Add seed rows to the session. Do not commit; the runner commits once for all seeders."""
