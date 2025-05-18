from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import BigInteger
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    username = Column(String, nullable=True)
    is_superadmin = Column(Boolean, default=False)

    channels = relationship("Channel", back_populates="admin")  # Ko‘p-kanalli aloqa


class Channel(Base):
    __tablename__ = "channels"

    id = Column(BigInteger, primary_key=True, index=True)  # Kanal ID
    name = Column(String, nullable=False)  # Kanal nomi
    channel_username = Column(String, nullable=True)

    admin_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    admin = relationship("User", back_populates="channels")  # Faqat bitta admin bo‘lishi mumkin




