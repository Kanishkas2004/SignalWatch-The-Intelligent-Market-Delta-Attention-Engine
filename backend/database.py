import datetime
import json
import os
from pathlib import Path
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Local: project-root DB. Vercel/serverless: writable /tmp.
_db_dir = Path("/tmp") if os.environ.get("VERCEL") else Path(".")
_db_path = _db_dir / "nexus_pulse.db"
DATABASE_URL = f"sqlite:///{_db_path.as_posix()}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    persona = Column(String(64), default="Momentum Trader")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    visit_snapshots = relationship("UserVisitSnapshot", back_populates="user", cascade="all, delete-orphan")


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(String(256), default="")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="watchlists")
    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"), nullable=False)
    symbol = Column(String(16), nullable=False, index=True)
    custom_notes = Column(Text, default="")
    tags = Column(String(256), default="[]")  # JSON encoded list of strings
    target_price = Column(Float, nullable=True)
    custom_sensitivity = Column(String(16), default="normal")  # high, normal, low
    added_at = Column(DateTime, default=datetime.datetime.utcnow)

    watchlist = relationship("Watchlist", back_populates="items")


class UserVisitSnapshot(Base):
    __tablename__ = "user_visit_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    visit_time = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    label = Column(String(128), default="Session Visit")
    prices_json = Column(Text, default="{}")  # JSON map: {symbol: price}

    user = relationship("User", back_populates="visit_snapshots")

    def get_prices(self) -> dict:
        try:
            return json.loads(self.prices_json)
        except Exception:
            return {}

    def set_prices(self, prices_dict: dict):
        self.prices_json = json.dumps(prices_dict)


class MarketAlert(Base):
    __tablename__ = "market_alerts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(16), index=True, nullable=False)
    alert_type = Column(String(32), nullable=False)  # VOLATILITY, VOLUME_SURGE, LEVEL_CROSS, CATALYST, DECOUPLING
    severity = Column(String(16), default="MEDIUM")  # HIGH, MEDIUM, LOW
    headline = Column(String(256), nullable=False)
    details = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
