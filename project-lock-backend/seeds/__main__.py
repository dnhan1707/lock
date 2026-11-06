import asyncio
import logging

from app.core.config import settings
from app.db.session import SessionLocal, engine
from seeds.seeders import SEEDERS

logger = logging.getLogger("seeds")


async def run_seeders() -> None:
    if settings.app_env == "production":
        raise SystemExit("Refusing to seed: APP_ENV is 'production'.")

    # All seeders share one transaction, so a failure leaves the database unchanged.
    async with SessionLocal() as session:
        try:
            for seeder_cls in SEEDERS:
                logger.info("Running %s", seeder_cls.__name__)
                await seeder_cls().run(session)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    logger.info("Seeding complete (%d seeder(s)).", len(SEEDERS))


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        await run_seeders()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
