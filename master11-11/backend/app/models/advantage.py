# backend/app/models/advantage.py
from sqlalchemy import Column, Integer, String, Text, DateTime # type: ignore
from app.database import Base
import datetime

class Advantage(Base):
    __tablename__ = "advantage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    desc = Column(Text, nullable=True)
    img = Column(String(512), nullable=True)
    destination = Column(String(256), nullable=True)
    time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
