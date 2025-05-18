from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot_bot.database.models import Base
from webApp.app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# E'tibor: init qilish uchun bu kerak
def init_db():
    Base.metadata.create_all(bind=engine)