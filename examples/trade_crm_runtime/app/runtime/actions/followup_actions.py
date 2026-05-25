"""
Followup Actions — Business Logic
===================================
Role: Implement followup domain actions.
"""

from typing import Any, Dict, List

from app.infrastructure.database import FollowupRepository


class FollowupActions:
    """Followup domain business actions."""

    def __init__(self):
        self._repo = FollowupRepository()

    def create_followup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new follow-up record."""
        required = ["customer_id", "content"]
        for field in required:
            if field not in params:
                return {"success": False, "result": None, "error": f"Missing required field: {field}"}

        if not params["content"].strip():
            return {"success": False, "result": None, "error": "Follow-up content cannot be empty"}

        followup = self._repo.create(params)
        return {
            "success": True,
            "result": {
                "followup_id": followup.followup_id,
                "customer_id": followup.customer_id,
                "followup_type": followup.followup_type,
                "followup_date": followup.followup_date,
            },
            "error": None
        }

    def list_followups(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List follow-ups for a customer."""
        customer_id = params.get("customer_id")
        if not customer_id:
            return {"success": False, "result": None, "error": "Missing required field: customer_id"}

        followups = self._repo.list_by_customer(
            customer_id=customer_id,
            limit=params.get("limit", 100),
        )
        return {
            "success": True,
            "result": {
                "count": len(followups),
                "followups": [
                    {
                        "followup_id": f.followup_id,
                        "customer_id": f.customer_id,
                        "content": f.content,
                        "followup_type": f.followup_type,
                        "followup_date": f.followup_date,
                        "next_followup_date": f.next_followup_date,
                    }
                    for f in followups
                ]
            },
            "error": None
        }