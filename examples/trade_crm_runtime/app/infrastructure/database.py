"""
Infrastructure: Database Layer
================================
Role: Pure data access — no business logic here.

Models: Customer, Followup (SQLModel, mapped from domain YAML)
Repository: CustomerRepository, FollowupRepository

AI principle: Business logic lives in runtime/actions/, not here.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select


# ─── Models ────────────────────────────────────────────────────────────────

class Customer(SQLModel, table=True):
    """Customer entity — corresponds to app/domain/customer.yaml"""
    __tablename__ = "customers"

    customer_id: str = Field(primary_key=True)
    company_name: str = Field(nullable=False, index=True)
    contact_name: str = Field(nullable=False)
    contact_email: str = Field(nullable=False)
    contact_phone: Optional[str] = Field(default=None)
    country: str = Field(nullable=False, index=True)
    business_type: Optional[str] = Field(default=None)
    contact_status: str = Field(default="new", index=True)
    notes: Optional[str] = Field(default=None)
    follow_up_count: int = Field(default=0)
    created_at: str = Field(default="")
    updated_at: str = Field(default="")

    @staticmethod
    def new_id() -> str:
        return f"CUST_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


class Followup(SQLModel, table=True):
    """Followup entity — corresponds to app/domain/followup.yaml"""
    __tablename__ = "followups"

    followup_id: str = Field(primary_key=True)
    customer_id: str = Field(nullable=False, index=True)
    content: str = Field(nullable=False)
    followup_type: str = Field(default="call")
    followup_date: str = Field(default="")
    next_followup_date: Optional[str] = Field(default=None)
    created_by: str = Field(default="system")

    @staticmethod
    def new_id() -> str:
        return f"FUP_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


# ─── Database Setup ─────────────────────────────────────────────────────────

_db_path = "data/crm.db"
_engine = None


def get_engine():
    """Get or create the SQLModel engine (singleton)."""
    global _engine
    if _engine is None:
        Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{_db_path}", echo=False)
    return _engine


def init_db() -> None:
    """Create all tables. Safe to call multiple times."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session."""
    return Session(get_engine())


# ─── Repositories ────────────────────────────────────────────────────────────

class CustomerRepository:
    """Pure data access for Customer. No business logic."""

    def create(self, data: Dict[str, Any]) -> Customer:
        now = datetime.utcnow().isoformat()
        customer = Customer(
            customer_id=data.get("customer_id") or Customer.new_id(),
            company_name=data["company_name"],
            contact_name=data["contact_name"],
            contact_email=data["contact_email"],
            contact_phone=data.get("contact_phone"),
            country=data["country"],
            business_type=data.get("business_type"),
            contact_status=data.get("contact_status", "new"),
            notes=data.get("notes"),
            follow_up_count=data.get("follow_up_count", 0),
            created_at=now,
            updated_at=now,
        )
        with get_session() as s:
            s.add(customer)
            s.commit()
            s.refresh(customer)
        return customer

    def get(self, customer_id: str) -> Optional[Customer]:
        with get_session() as s:
            return s.get(Customer, customer_id)

    def list(self, contact_status: Optional[str] = None, country: Optional[str] = None, limit: int = 100) -> List[Customer]:
        with get_session() as s:
            query = select(Customer)
            if contact_status:
                query = query.where(Customer.contact_status == contact_status)
            if country:
                query = query.where(Customer.country == country)
            query = query.limit(limit)
            return list(s.exec(query).all())

    def update(self, customer_id: str, data: Dict[str, Any]) -> Optional[Customer]:
        with get_session() as s:
            customer = s.get(Customer, customer_id)
            if not customer:
                return None
            for key, value in data.items():
                if key not in ("customer_id", "created_at"):
                    setattr(customer, key, value)
            customer.updated_at = datetime.utcnow().isoformat()
            s.add(customer)
            s.commit()
            s.refresh(customer)
            return customer

    def delete(self, customer_id: str) -> bool:
        with get_session() as s:
            customer = s.get(Customer, customer_id)
            if not customer:
                return False
            s.delete(customer)
            s.commit()
            return True


class FollowupRepository:
    """Pure data access for Followup. No business logic."""

    def create(self, data: Dict[str, Any]) -> Followup:
        followup = Followup(
            followup_id=data.get("followup_id") or Followup.new_id(),
            customer_id=data["customer_id"],
            content=data["content"],
            followup_type=data.get("followup_type", "call"),
            followup_date=datetime.utcnow().isoformat(),
            next_followup_date=data.get("next_followup_date"),
            created_by=data.get("created_by", "system"),
        )
        with get_session() as s:
            s.add(followup)
            s.commit()
            s.refresh(followup)
        return followup

    def get(self, followup_id: str) -> Optional[Followup]:
        with get_session() as s:
            return s.get(Followup, followup_id)

    def list_by_customer(self, customer_id: str, limit: int = 100) -> List[Followup]:
        with get_session() as s:
            query = select(Followup).where(Followup.customer_id == customer_id).limit(limit)
            return list(s.exec(query).all())

    def delete(self, followup_id: str) -> bool:
        with get_session() as s:
            followup = s.get(Followup, followup_id)
            if not followup:
                return False
            s.delete(followup)
            s.commit()
            return True