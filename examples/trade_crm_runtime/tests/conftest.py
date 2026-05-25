"""
Test configuration and fixtures for trade_crm_runtime tests.
"""
import pytest
import sys
import tempfile
import uuid
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from sqlmodel import SQLModel, Session


# Counter for unique ID generation in tests
_id_counter = 0


def _unique_customer_id():
    """Generate unique customer ID for tests."""
    global _id_counter
    _id_counter += 1
    return f"CUST_TEST_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{_id_counter}"


def _unique_followup_id():
    """Generate unique followup ID for tests."""
    global _id_counter
    _id_counter += 1
    return f"FUP_TEST_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{_id_counter}"


@pytest.fixture(scope="function")
def test_db_path():
    """Provide a temporary database file path for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture(scope="function")
def test_engine(test_db_path):
    """Create a SQLite engine backed by a temp file for each test."""
    from sqlmodel import create_engine
    from app.infrastructure.database import SQLModel
    
    engine = create_engine(f"sqlite:///{test_db_path}", echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def setup_test_engine(test_db_path):
    """Override the global engine to use a test database and patch ID generation."""
    from app.infrastructure import database
    from app.infrastructure.database import Customer, Followup
    from sqlmodel import create_engine
    from app.infrastructure.database import SQLModel
    
    # Create a new engine for testing
    test_engine = create_engine(f"sqlite:///{test_db_path}", echo=False)
    SQLModel.metadata.create_all(test_engine)
    
    # Patch globally
    database._engine = test_engine
    database._db_path = test_db_path
    
    # Patch ID generation to be unique
    original_customer_new_id = Customer.new_id
    original_followup_new_id = Followup.new_id
    Customer.new_id = staticmethod(_unique_customer_id)
    Followup.new_id = staticmethod(_unique_followup_id)
    
    yield test_engine
    
    # Restore
    Customer.new_id = original_customer_new_id
    Followup.new_id = original_followup_new_id
    database._engine = None
    database._db_path = "data/crm.db"
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def customer_actions(setup_test_engine):
    """Provide CustomerActions with test database."""
    from app.runtime.actions.customer_actions import CustomerActions
    return CustomerActions()


@pytest.fixture(scope="function")
def followup_actions(setup_test_engine):
    """Provide FollowupActions with test database."""
    from app.runtime.actions.followup_actions import FollowupActions
    return FollowupActions()


@pytest.fixture(scope="function")
def unique_id():
    """Generate a unique ID suffix for test data to avoid ID collisions."""
    return uuid.uuid4().hex[:8]


@pytest.fixture(scope="function")
def sample_customer_data(unique_id):
    """Provide sample customer data for tests."""
    return {
        "company_name": f"Acme Corp {unique_id}",
        "contact_name": "John Doe",
        "contact_email": f"john.{unique_id}@acme.com",
        "country": "USA",
        "contact_phone": "+1-555-0100",
        "business_type": "Technology",
        "contact_status": "new",
        "notes": "Test customer",
    }


@pytest.fixture(scope="function")
def sample_followup_data():
    """Provide sample followup data for tests."""
    return {
        "content": "Initial contact call",
        "followup_type": "call",
    }
