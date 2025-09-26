# database.py

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime
import os 
from passlib.context import CryptContext

# DATABASE_URL = "mysql+mysqlconnector://root:Venu2425@localhost/face_search_db"
DATABASE_URL = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255))

class Guest(Base):
    __tablename__ = "guests"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    mobile_number = Column(String(20), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    activities = relationship("ActivityLog", back_populates="guest")
    downloads = relationship("DownloadLog", back_populates="guest")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    guest_id = Column(Integer, ForeignKey("guests.id"))
    guest = relationship("Guest", back_populates="activities")
    action = Column(String(255))
    details = Column(String(1024), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class CollectionLog(Base):
    __tablename__ = "collection_logs"
    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String(255), unique=True)
    upload_datetime = Column(DateTime, default=datetime.datetime.utcnow)
    source_folder = Column(String(1024))
    location = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)    

class DownloadLog(Base):
    __tablename__ = "download_logs"
    id = Column(Integer, primary_key=True, index=True)
    guest_id = Column(Integer, ForeignKey("guests.id"))
    guest = relationship("Guest", back_populates="downloads")
    image_paths = Column(Text)
    payment_confirmed_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(50), default="Pending Print")

def create_db_and_tables():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"--- FATAL ERROR creating database tables: {e} ---"); raise e

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# --- MOVED HERE FROM main_milvus.py ---
def log_activity(db_session: SessionLocal, guest_id: int, action: str, details: str = None):
    """Logs a guest activity to the database."""
    new_log = ActivityLog(guest_id=guest_id, action=action, details=details)
    db_session.add(new_log)
    db_session.commit()

    