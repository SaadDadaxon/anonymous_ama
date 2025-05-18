from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from bot_bot.config import DATABASE_URL
from .models import Base

# Asinxron bazaga ulanish
engine = create_async_engine(DATABASE_URL, echo=True)

# Asinxron sessiya yaratish
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Bazani yaratish funksiyasi
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)



