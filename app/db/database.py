from datetime import datetime
from functools import wraps
import re
from loguru import logger

from sqlalchemy import func, TIMESTAMP, Integer, text,create_engine
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, scoped_session
from app.config import settings

database_url = settings.DB_URL

sync_database_url = str(database_url).replace('postgresql+asyncpg', 'postgresql')
sync_engine = create_engine(sync_database_url)
sync_session_factory = sessionmaker(bind=sync_engine)
sync_session = scoped_session(sync_session_factory)


engine = create_async_engine(url=str(database_url))
async_session_maker = async_sessionmaker(engine, class_=AsyncSession)
def connection(isolation_level=None):
    def decorator(method):
        try:
            @wraps(method)
            async def wrapper(*args, **kwargs):
                async with async_session_maker() as session:
                    try:
                        if isolation_level:
                            await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
                        # Выполняем декорированный метод
                        return await method(*args, session=session, **kwargs)
                    except Exception as e:
                        logger.error(e)
                        await session.rollback()  # Откатываем сессию при ошибке
                        raise e  # Поднимаем исключение дальше
                    finally:
                        await session.close()  # Закрываем сессию
            return wrapper
        except Exception as e:
            logger.error(e)
    return decorator


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    @classmethod
    @property
    def __tablename__(cls) -> str:
        cls.__name__ = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower() + 's'
        return cls.__name__

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
