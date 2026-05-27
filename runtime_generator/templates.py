"""Code generators for each file type."""

from __future__ import annotations
from typing import Any


# ---------------------------------------------------------------------------
# engine.py
# ---------------------------------------------------------------------------

def engine_py(name: str, entities: list[Any]) -> str:
    """Generate app/runtime/engine.py — CRUD action handlers."""

    entity_handlers = []
    for e in entities:
        domain = e.table_name
        pascal = _to_pascal(e.name)
        field_names = ", ".join('"' + f.name + '"' for f in e.fields)

        handler = (
            "\n        # ---- " + e.name + " ----\n"
            "        def _create_" + domain + "(params: dict) -> dict:\n"
            '            """Create a new ' + e.name + ' record."""\n'
            "            from app.infrastructure.models import " + pascal + "Model\n"
            "            from sqlmodel import Session\n"
            "            session = _get_session()\n"
            "            record = " + pascal + "Model(**{k: v for k, v in params.items() if k in [" + field_names + "]})\n"
            "            session.add(record)\n"
            "            session.commit()\n"
            "            session.refresh(record)\n"
            "            return {\"success\": True, \"result\": record.model_dump()}\n"
            "\n"
            "        def _list_" + domain + "s(params: dict) -> dict:\n"
            '            """List ' + e.name + ' records with optional filters."""\n'
            "            from sqlmodel import Session, select\n"
            "            from app.infrastructure.models import " + pascal + "Model\n"
            "            session = _get_session()\n"
            "            limit = params.get(\"limit\", 100)\n"
            "            query = select(" + pascal + "Model).limit(limit)\n"
            "            results = session.exec(query).all()\n"
            "            return {\n"
            "                \"success\": True,\n"
            "                \"result\": [r.model_dump() for r in results],\n"
            "                \"pagination\": {\"page\": 1, \"per_page\": limit, \"total\": len(results)},\n"
            "            }\n"
            "\n"
            "        def _get_" + domain + "(params: dict) -> dict:\n"
            '            """Get a single ' + e.name + ' by ID."""\n'
            "            from sqlmodel import Session, select\n"
            "            from app.infrastructure.models import " + pascal + "Model\n"
            "            session = _get_session()\n"
            "            record = session.get(" + pascal + "Model, params[\"id\"])\n"
            "            if not record:\n"
            "                return {\"success\": False, \"error\": \"" + e.name + " not found\"}\n"
            "            return {\"success\": True, \"result\": record.model_dump()}\n"
            "\n"
            "        def _update_" + domain + "(params: dict) -> dict:\n"
            '            """Update a ' + e.name + ' record."""\n'
            "            from sqlmodel import Session\n"
            "            from app.infrastructure.models import " + pascal + "Model\n"
            "            session = _get_session()\n"
            "            record = session.get(" + pascal + "Model, params[\"id\"])\n"
            "            if not record:\n"
            "                return {\"success\": False, \"error\": \"" + e.name + " not found\"}\n"
            "            for key, value in params.items():\n"
            "                if key != \"id\" and hasattr(record, key):\n"
            "                    setattr(record, key, value)\n"
            "            session.commit()\n"
            "            session.refresh(record)\n"
            "            return {\"success\": True, \"result\": record.model_dump()}\n"
            "\n"
            "        def _delete_" + domain + "(params: dict) -> dict:\n"
            '            """Delete a ' + e.name + ' record."""\n'
            "            from sqlmodel import Session\n"
            "            from app.infrastructure.models import " + pascal + "Model\n"
            "            session = _get_session()\n"
            "            record = session.get(" + pascal + "Model, params[\"id\"])\n"
            "            if not record:\n"
            "                return {\"success\": False, \"error\": \"" + e.name + " not found\"}\n"
            "            session.delete(record)\n"
            "            session.commit()\n"
            "            return {\"success\": True, \"result\": {\"deleted\": params[\"id\"]}}\n"
        )
        entity_handlers.append(handler)

    action_map_entries = []
    for e in entities:
        domain = e.table_name
        action_map_entries.append("        \"create_" + domain + "\": _create_" + domain + ",")
        action_map_entries.append("        \"list_" + domain + "s\": _list_" + domain + "s,")
        action_map_entries.append("        \"get_" + domain + "\": _get_" + domain + ",")
        action_map_entries.append("        \"update_" + domain + "\": _update_" + domain + ",")
        action_map_entries.append("        \"delete_" + domain + "\": _delete_" + domain + ",")

    _h = "\n".join(entity_handlers)
    _a = "\n".join(action_map_entries)
    default_db = "data/" + name + ".db"

    tmpl = (
        '"""Business Runtime Engine - generated for: " + name + """\n'
        + "\n"
        + "from __future__ import annotations\n"
        + "from typing import Any, Callable\n"
        + "from sqlmodel import create_engine, Session\n"
        + "\n"
        + "# Database engine (lazy init)\n"
        + "_db_engine = None\n"
        + "\n"
        + "def _get_engine():\n"
        + "    global _db_engine\n"
        + "    if _db_engine is None:\n"
        + "        from runtime.yaml import config\n"
        + '        db_path = config.get("infrastructure", {}).get("database", {}).get("path", "' + default_db + '")\n'
        + '        _db_engine = create_engine(f"sqlite:///{db_path}")\n'
        + "    return _db_engine\n"
        + "\n"
        + "def _get_session() -> Session:\n"
        + "    return Session(_get_engine())\n"
        + "\n"
        + "class RuntimeEngine:\n"
        + '    """Execute business actions with validation and state machine support."""\n'
        + "\n"
        + "    def __init__(self):\n"
        + "        self.actions: dict[str, Callable] = {}\n"
        + "        self.action_map: dict[str, Callable] = {}\n"
        + "        self._register_actions()\n"
        + "\n"
        + _h + "\n"
        + "\n"
        + "    def _register_actions(self):\n"
        + "        self.action_map = {\n"
        + "        " + _a.replace("\n", "\n        ") + "\n"
        + "        }\n"
        + "\n"
        + "    def list_actions(self) -> list[str]:\n"
        + '        """Return all registered action names."""\n'
        + "        return list(self.action_map.keys())\n"
        + "\n"
        + "    def execute(self, action: str, params: dict | None = None) -> dict:\n"
        + '        """Execute an action by name."""\n'
        + "        params = params or {}\n"
        + '        if action not in self.action_map:\n'
        + '            return {"success": False, "error": "Unknown action: " + action}\n'
        + "        try:\n"
        + "            return self.action_map[action](params)\n"
        + "        except Exception as e:\n"
        + '            return {"success": False, "error": str(e)}\n'
        + "\n"
        + "    def validate_constraints(self, entity: str, data: dict) -> list[str]:\n"
        + '        """Validate data against entity constraints."""\n'
        + "        errors = []\n"
        + "        return errors\n"
    )
    return tmpl


# ---------------------------------------------------------------------------
# mcp_server.py
# ---------------------------------------------------------------------------

def mcp_server_py(name: str, entities: list[Any]) -> str:
    """Generate mcp_server.py - MCP JSON-RPC server adapter."""
    tool_defs = []
    engine_calls = []

    for e in entities:
        domain = e.table_name
        pascal = _to_pascal(e.name)

        tool_def = (
            "        {\n"
            '            "name": "mcp_' + domain + '_list_' + domain + 's",\n'
            '            "description": "List ' + e.name + ' records",\n'
            '            "inputSchema": {\n'
            '                "type": "object",\n'
            '                "properties": {\n'
            '                    "limit": {"type": "integer", "default": 100}\n'
            "                }\n"
            "            }\n"
            "        }"
        )
        tool_defs.append(tool_def)
        engine_calls.append("            engine_actions[\"list_" + domain + "s\"]")

    tool_defs_json = ",\n".join(tool_defs)
    engine_calls_json = ",\n".join(engine_calls)

    return (
        '"""MCP Server - generated for: " + name + """\n'
        + "\n"
        + "import json\n"
        + "from typing import Any\n"
        + "\n"
        + "TOOL_DEFINITIONS = [\n"
        + tool_defs_json + "\n"
        + "]\n"
        + "\n"
        + "TOOL_MAP = {\n"
        + engine_calls_json + "\n"
        + "}\n"
        + "\n"
        + "def handle_request(req: dict) -> dict:\n"
        + '    method = req.get("method")\n'
        + '    req_id = req.get("id")\n'
        + "    params = req.get(\"params\", {})\n"
        + '    if method == "tools/list":\n'
        + "        return _jsonrpc_success(req_id, {\"tools\": TOOL_DEFINITIONS})\n"
        + '    elif method == "tools/call":\n'
        + '        tool_name = params.get("name", "")\n'
        + '        arguments = params.get("arguments", {})\n'
        + "        if tool_name in TOOL_MAP:\n"
        + "            result = TOOL_MAP[tool_name](arguments)\n"
        + "            return _jsonrpc_success(req_id, result)\n"
        + "        return _jsonrpc_error(req_id, -32601, \"Method not found\")\n"
        + "    return _jsonrpc_error(req_id, -32601, \"Method not found\")\n"
        + "\n"
        + "def _jsonrpc_success(req_id, result):\n"
        + '    return {"jsonrpc": "2.0", "id": req_id, "result": result}\n'
        + "\n"
        + "def _jsonrpc_error(req_id, code, message):\n"
        + '    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}\n'
        + "\n"
        + "def main():\n"
        + "    import sys, json\n"
        + "    for line in sys.stdin:\n"
        + "        req = json.loads(line)\n"
        + "        resp = handle_request(req)\n"
        + "        print(json.dumps(resp))\n"
        + "        sys.stdout.flush()\n"
    )


# ---------------------------------------------------------------------------
# models.py
# ---------------------------------------------------------------------------

def models_py(entities: list[Any]) -> str:
    """Generate app/infrastructure/models.py - SQLModel table definitions."""
    imports = [
        "from __future__ import annotations",
        "from typing import Optional",
        "from sqlmodel import Field, SQLModel",
    ]
    classes = []
    for e in entities:
        pascal = _to_pascal(e.name)
        field_lines = []
        for f in e.fields:
            extra = []
            if f.primary_key:
                extra.append("primary_key=True")
            if f.required:
                extra.append("nullable=False")
            if f.unique:
                extra.append("unique=True")
            if f.indexed:
                extra.append("index=True")
            if f.default is not None:
                extra.append("default=" + repr(f.default))
            if f.enum_values:
                extra.append(
                    "schema_extra={\"json_schema_extra\": {\"enum\": " + repr(f.enum_values) + "}}"
                )
            opts = ", ".join(extra)
            field_lines.append("    " + f.name + ": " + f.type + " = Field(" + opts + ")")
        field_block = "\n".join(field_lines)
        cls = (
            "class " + pascal + "Model(SQLModel, table=True):\n"
            '    """Generated table model for ' + e.name + '."""\n'
            '    __tablename__ = "' + e.table_name + '"\n'
            + field_block
        )
        classes.append(cls)
    return "\n\n".join(imports) + "\n\n\n" + "\n\n\n".join(classes) + "\n"


# ---------------------------------------------------------------------------
# runtime.yaml
# ---------------------------------------------------------------------------

def runtime_yaml(
    name: str,
    description: str,
    author: str,
    entities: list[Any],
    state_machines: dict[str, Any],
) -> str:
    """Generate config/runtime.yaml."""
    import yaml

    entity_configs = []
    for e in entities:
        cfg = {
            "name": e.name,
            "table": e.table_name,
            "fields": [
                {
                    "name": f.name,
                    "type": f.type,
                    "required": f.required,
                }
                for f in e.fields
            ],
        }
        entity_configs.append(cfg)

    data = {
        "name": name,
        "description": description,
        "author": author,
        "version": "1.0",
        "infrastructure": {
            "database": {
                "path": "data/" + name + ".db",
            }
        },
        "entities": entity_configs,
        "state_machines": state_machines,
    }
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


# ---------------------------------------------------------------------------
# domain.yaml
# ---------------------------------------------------------------------------

def domain_yaml(entity) -> str:
    """Generate config/domains/{entity}.yaml."""
    import yaml

    data = {
        "name": entity.name,
        "table_name": entity.table_name,
        "description": entity.description,
        "fields": [
            {
                "name": f.name,
                "type": f.type,
                "required": f.required,
                "primary_key": f.primary_key,
            }
            for f in entity.fields
        ],
    }
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


# ---------------------------------------------------------------------------
# example workflow
# ---------------------------------------------------------------------------

def example_workflow_yaml(name: str, entities: list[Any]) -> str:
    """Generate an example workflow YAML."""
    return (
        "workflow:\n"
        '  name: "example-workflow"\n'
        '  version: "1.0"\n'
        "  description: Example workflow for " + name + "\n"
        "\n"
        "tasks:\n"
        "  - id: step_1\n"
        "    type: prompt\n"
        '    config:\n'
        '      prompt: "Hello! This is a placeholder prompt."\n'
        "      model: gpt-4o\n"
        "      max_tokens: 50\n"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _indent(text: str, spaces: int) -> str:
    """Indent each line of text by `spaces` spaces."""
    pad = " " * spaces
    return "\n".join(pad + line for line in text.split("\n"))


def _to_pascal(name: str) -> str:
    """Convert snake_case or kebab-case to PascalCase."""
    parts = name.replace("-", "_").split("_")
    return "".join(p.capitalize() for p in parts if p)


def _to_snake(name: str) -> str:
    """Convert any-case to snake_case."""
    import re
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    name = re.sub(r"[-]+", "_", name)
    return name.lower()


def _generate_field_schema(fields, exclude: list[str] | None = None) -> dict:
    """Generate a JSON schema fragment for a list of fields."""
    exclude = exclude or []
    properties = {}
    required = []
    for f in fields:
        if f.name in exclude:
            continue
        prop = {"type": _js_type(f.type)}
        if f.enum_values:
            prop["enum"] = f.enum_values
        if f.default is not None:
            prop["default"] = f.default
        properties[f.name] = prop
        if f.required:
            required.append(f.name)
    return {"type": "object", "properties": properties, "required": required}


def _generate_required_list(fields) -> list[str]:
    """Return list of required field names."""
    return [f.name for f in fields if f.required]


def _js_type(field_type: str) -> str:
    """Map internal type to JSON Schema type."""
    mapping = {
        "string": "string",
        "text": "string",
        "integer": "integer",
        "float": "number",
        "boolean": "boolean",
        "datetime": "string",
        "date": "string",
        "json": "object",
    }
    return mapping.get(field_type, "string")


# ---------------------------------------------------------------------------
# AI prompt documentation
# ---------------------------------------------------------------------------

def ai_prompt_md(name: str, description: str, entities: list[Any]) -> str:
    """Generate AI.md — AI-readable documentation of all actions and constraints.

    This file is the AI's primary interface for understanding what it can do
    and what business rules apply. It should be passed to the AI as system
    context alongside the MCP tool definitions.

    Generated content includes:
    - Business overview
    - Entity descriptions (what each entity represents)
    - Action catalog with full semantic descriptions
    - Field-level constraints and business rules
    - Constraint rules expressed in plain English
    - Error handling guidance
    """

    # Build sections
    lines = []

    # Header
    lines.append(f"# {name} — AI Action Reference")
    lines.append("")
    if description:
        lines.append(f"_{description}_")
        lines.append("")
    lines.append("This file documents all available actions, their constraints, and business rules.")
    lines.append("Use it as system context when reasoning about data operations.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Entity overview
    if entities:
        lines.append("## Entities")
        lines.append("")
        for e in entities:
            bm = getattr(e, "business_meaning", "") or e.description or "No description"
            lines.append(f"- **{e.name}** — {bm}")
        lines.append("")

    # Action catalog
    lines.append("## Available Actions")
    lines.append("")
    lines.append("Each action maps to a single MCP tool. Call them by name with the required parameters.")
    lines.append("")

    for e in entities:
        pascal = _to_pascal(e.name)
        domain = e.table_name
        bm = getattr(e, "business_meaning", "") or e.description

        lines.append(f"### {pascal} Management")
        lines.append("")
        if bm:
            lines.append(f"A {pascal} represents: {bm}")
            lines.append("")

        # list action
        lines.append(f"#### list_{domain}s")
        lines.append("")
        lines.append(f"Query {pascal} records with optional filters and pagination.")
        lines.append("")
        lines.append("**Parameters:**")
        lines.append("")
        lines.append("| Parameter | Type | Required | Description |")
        lines.append("|-----------|------|----------|-------------|")
        lines.append("| `limit` | integer | No | Max records to return (default: 20, max: 100) |")
        lines.append("| `offset` | integer | No | Skip first N records for pagination |")
        lines.append("| `order_by` | string | No | Field to sort by (prefix `-` for descending) |")
        # Dynamic filter params
        filterable = [f for f in e.fields if not f.primary_key and f.type in ("string", "text", "integer", "enum")]
        for f in filterable[:5]:
            fdesc = f"Filter by {f.name}" + (f" (one of: {', '.join(f.enum_values)})" if f.enum_values else "")
            lines.append(f"| `{f.name}` | {f.type} | No | {fdesc} |")
        lines.append("")
        lines.append("**Returns:** `{success: bool, results: ...}`")
        lines.append("")
        lines.append("**Errors:** `success: false` when filters are invalid.")
        lines.append("")

        # get action
        lines.append(f"#### get_{domain}")
        lines.append("")
        lines.append(f"Retrieve a single {pascal} by its ID.")
        lines.append("")
        lines.append("**Parameters:**")
        lines.append("")
        lines.append("| Parameter | Type | Required | Description |")
        lines.append("|-----------|------|----------|-------------|")
        lines.append(f"| `id` | string | **Yes** | The unique ID of the {pascal} |")
        lines.append("")
        lines.append(f"**Returns:** `success: true, result: {pascal}Record`")
        lines.append("")
        lines.append("**Errors:** `success: false` if no record matches.")
        lines.append("")

        # create action
        lines.append(f"#### create_{domain}")
        lines.append("")
        lines.append(f"Create a new {pascal} record.")
        lines.append("")
        lines.append("**Parameters:**")
        lines.append("")
        lines.append("| Parameter | Type | Required | Description |")
        lines.append("|-----------|------|----------|-------------|")
        required_fields = [f for f in e.fields if f.required and not f.primary_key]
        optional_fields = [f for f in e.fields if not f.required and not f.primary_key]
        for f in required_fields:
            enum_note = f" (one of: {', '.join(f.enum_values)})" if f.enum_values else ""
            fdesc = f.description or f"Field: {f.name}" + enum_note
            lines.append(f"| `{f.name}` | {f.type} | **Yes** | {fdesc} |")
        for f in optional_fields:
            enum_note = f" (one of: {', '.join(f.enum_values)})" if f.enum_values else ""
            fdesc = f.description or f"Field: {f.name}" + enum_note
            lines.append(f"| `{f.name}` | {f.type} | No | {fdesc} |")
        lines.append("")

        # Constraints
        constraints = getattr(e, "constraints", [])
        if constraints:
            lines.append("**Business Rules (enforced):**")
            lines.append("")
            for c in constraints:
                lines.append(f"- {c.to_ai_description()}")
            lines.append("")

        lines.append(f"**Returns:** `success: true, result: {pascal}Record`")
        lines.append("")
        lines.append("**Errors:** `success: false` when validation fails.")
        lines.append("")

        # update action
        lines.append(f"#### update_{domain}")
        lines.append("")
        lines.append(f"Update an existing {pascal} record. Only provided fields are updated (partial update).")
        lines.append("")
        lines.append("**Parameters:**")
        lines.append("")
        lines.append("| Parameter | Type | Required | Description |")
        lines.append("|-----------|------|----------|-------------|")
        lines.append(f"| `id` | string | **Yes** | The ID of the {pascal} to update |")
        updatable = [f for f in e.fields if not f.primary_key]
        for f in updatable:
            enum_note = f" (one of: {', '.join(f.enum_values)})" if f.enum_values else ""
            req = "**Yes**" if f.required else "No"
            fdesc = f.description or f"Field: {f.name}" + enum_note
            lines.append(f"| `{f.name}` | {f.type} | {req} | {fdesc} |")
        lines.append("")
        if constraints:
            lines.append("**Business Rules (enforced):**")
            lines.append("")
            for c in constraints:
                lines.append(f"- {c.to_ai_description()}")
            lines.append("")
        lines.append(f"**Returns:** `success: true, result: {pascal}Record`")
        lines.append("")
        lines.append("**Errors:** `success: false` if no record matches.")
        lines.append("")

        # delete action
        lines.append(f"#### delete_{domain}")
        lines.append("")
        lines.append(f"Permanently delete a {pascal} record.")
        lines.append("")
        lines.append("**Parameters:**")
        lines.append("")
        lines.append("| Parameter | Type | Required | Description |")
        lines.append("|-----------|------|----------|-------------|")
        lines.append(f"| `id` | string | **Yes** | The ID of the {pascal} to delete |")
        lines.append("")
        lines.append(f"**Returns:** `success: true`")
        lines.append("")
        lines.append("**Errors:** `success: false` if no record matches.")
        lines.append("")

        lines.append("---")
        lines.append("")

    # General guidance
    lines.append("## General Guidance for AI Agents")
    lines.append("")
    lines.append("1. **Always check constraints before writing.** Read the business rules for each action.")
    lines.append("2. **Validate before create/update.** Call the action and inspect the result.")
    lines.append("3. **Partial updates.** The `update_*` actions support partial updates — only include fields that changed.")
    lines.append("4. **Pagination.** Use `limit` and `offset` to page through large result sets.")
    lines.append("5. **Error handling.** All actions return `{success: bool, result/error: ...}`.")
    lines.append("   - On `success: false`, inspect `error` and retry with corrected input.")
    lines.append("6. **Unique constraints.** If `create` fails with a uniqueness error, query existing records first.")
    lines.append("")

    return "\n".join(lines)
