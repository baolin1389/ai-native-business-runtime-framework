"""
Runtime Engine
==============
Role: Central execution hub. Routes actions to handlers.

AI principle: All business operations go through engine.execute().
MCP tools call engine.execute() — they never touch repositories directly.
"""

from typing import Any, Dict, List, Optional


class RuntimeEngine:
    """
    Central execution engine for the Trade CRM Runtime.

    Usage:
        engine = RuntimeEngine('runtime.yaml')
        result = engine.execute('create_customer', {'company_name': 'Berlin GmbH', ...})
    """

    def __init__(self, config_path: str = "runtime.yaml"):
        from app.runtime.actions.customer_actions import CustomerActions
        from app.runtime.actions.followup_actions import FollowupActions

        self._config = self._load_config(config_path)
        self._customer = CustomerActions()
        self._followup = FollowupActions()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a named action.

        Args:
            action: Action name (e.g., 'create_customer', 'add_followup')
            params: Action parameters dict

        Returns:
            {'success': bool, 'result': {...}, 'error': str or None}
        """
        params = params or {}

        # Dispatch to appropriate domain handler
        if action == "create_customer":
            return self._customer.create_customer(params)
        elif action == "list_customers":
            return self._customer.list_customers(params)
        elif action == "get_customer":
            return self._customer.get_customer(params)
        elif action == "update_customer":
            return self._customer.update_customer(params)
        elif action == "add_followup":
            return self._followup.create_followup(params)
        elif action == "list_followups":
            return self._followup.list_followups(params)
        else:
            return {"success": False, "result": None, "error": f"Unknown action: {action}"}

    def list_actions(self) -> List[str]:
        """Return all available actions."""
        return [
            "create_customer", "list_customers", "get_customer", "update_customer",
            "add_followup", "list_followups"
        ]

    def list_domains(self) -> List[str]:
        """Return all domain names."""
        return ["customer", "followup"]