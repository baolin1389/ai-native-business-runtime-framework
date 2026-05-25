"""
Customer Actions — Business Logic
===================================
Role: Implement customer domain actions.

AI principle: Actions contain business logic, NOT data access.
Data access goes through CustomerRepository.
"""

from typing import Any, Dict, List

from app.infrastructure.database import CustomerRepository


class CustomerActions:
    """Customer domain business actions."""

    def __init__(self):
        self._repo = CustomerRepository()

    def create_customer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer."""
        required = ["company_name", "contact_name", "contact_email", "country"]
        for field in required:
            if field not in params:
                return {"success": False, "result": None, "error": f"Missing required field: {field}"}

        # Simple email format validation
        email = params["contact_email"]
        if "@" not in email or "." not in email.split("@")[1]:
            return {"success": False, "result": None, "error": "Invalid email format"}

        customer = self._repo.create(params)
        return {
            "success": True,
            "result": {
                "customer_id": customer.customer_id,
                "company_name": customer.company_name,
                "contact_status": customer.contact_status,
                "created_at": customer.created_at,
            },
            "error": None
        }

    def list_customers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List customers with optional filters."""
        customers = self._repo.list(
            contact_status=params.get("contact_status"),
            country=params.get("country"),
            limit=params.get("limit", 100),
        )
        return {
            "success": True,
            "result": {
                "count": len(customers),
                "customers": [
                    {
                        "customer_id": c.customer_id,
                        "company_name": c.company_name,
                        "contact_name": c.contact_name,
                        "contact_email": c.contact_email,
                        "country": c.country,
                        "contact_status": c.contact_status,
                    }
                    for c in customers
                ]
            },
            "error": None
        }

    def get_customer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a customer by ID."""
        customer_id = params.get("customer_id")
        if not customer_id:
            return {"success": False, "result": None, "error": "Missing required field: customer_id"}

        customer = self._repo.get(customer_id)
        if not customer:
            return {"success": False, "result": None, "error": f"Customer not found: {customer_id}"}

        return {
            "success": True,
            "result": {
                "customer_id": customer.customer_id,
                "company_name": customer.company_name,
                "contact_name": customer.contact_name,
                "contact_email": customer.contact_email,
                "contact_phone": customer.contact_phone,
                "country": customer.country,
                "business_type": customer.business_type,
                "contact_status": customer.contact_status,
                "notes": customer.notes,
                "follow_up_count": customer.follow_up_count,
                "created_at": customer.created_at,
                "updated_at": customer.updated_at,
            },
            "error": None
        }

    def update_customer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update customer fields. Increments follow_up_count on status change."""
        customer_id = params.get("customer_id")
        if not customer_id:
            return {"success": False, "result": None, "error": "Missing required field: customer_id"}

        # Get current customer
        customer = self._repo.get(customer_id)
        if not customer:
            return {"success": False, "result": None, "error": f"Customer not found: {customer_id}"}

        # If contact_status is changing, increment follow_up_count
        update_data = dict(params)
        if "contact_status" in params and params["contact_status"] != customer.contact_status:
            update_data["follow_up_count"] = customer.follow_up_count + 1

        updated = self._repo.update(customer_id, update_data)
        return {
            "success": True,
            "result": {
                "customer_id": updated.customer_id,
                "contact_status": updated.contact_status,
                "follow_up_count": updated.follow_up_count,
                "updated_at": updated.updated_at,
            },
            "error": None
        }