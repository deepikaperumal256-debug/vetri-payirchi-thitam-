from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    goal = Column(String, nullable=False)
    intensity = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    original_plan = Column(Text, nullable=False)
    updated_plan = Column(Text)
    nutrition_tip = Column(Text)
    last_feedback = Column(Text)
    updated_at = Column(DateTime)


def init_db():
    Base.metadata.create_all(engine)


# ---- CRUD helpers -------------------------------------------------------
def save_user(db, data):
    user = db.query(User).filter_by(user_id=data.user_id).first()
    if user:  # re-registering with same ID refreshes the profile
        for k in ("username", "age", "weight", "goal", "intensity"):
            setattr(user, k, getattr(data, k))
    else:
        user = User(**data.model_dump())
        db.add(user)
    db.commit()
    return user


def save_plan(db, user_id, plan, tip):
    row = db.query(Plan).filter_by(user_id=user_id).first()
    if row:
        row.original_plan, row.nutrition_tip = plan, tip
        row.updated_plan = row.last_feedback = row.updated_at = None
    else:
        db.add(Plan(user_id=user_id, original_plan=plan, nutrition_tip=tip))
    db.commit()


def get_user(db, user_id):
    return db.query(User).filter_by(user_id=user_id).first()


def get_plan(db, user_id):
    return db.query(Plan).filter_by(user_id=user_id).first()


def update_plan(db, user_id, new_plan, feedback):
    row = get_plan(db, user_id)
    row.updated_plan = new_plan
    row.last_feedback = feedback
    row.updated_at = datetime.utcnow()
    db.commit()


def get_all_users_with_plans(db):
    users = db.query(User).order_by(User.created_at.desc()).all()
    plans = {p.user_id: p for p in db.query(Plan).all()}
    return [(u, plans.get(u.user_id)) for u in users]


def delete_user(db, user_id):
    db.query(Plan).filter_by(user_id=user_id).delete()
    db.query(User).filter_by(user_id=user_id).delete()
    db.commit()
