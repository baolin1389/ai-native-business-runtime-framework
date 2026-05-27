"""Code generation templates for the RuntimeGenerator.

Each method returns a string of generated code/config
that gets written to the output directory.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any


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
    """Generate runtime.yaml."""

    entity_lines = []
    for e in entities:
        entity_lines.append(f"  - name: {e.name}\n")
        entity_lines.append(f"    table_name: {e.table_name}\n")
        entity_lines.append(f'    description: "{e.description}"\n' if e.description else f'    description: "{e.name} entity"\n')
        entity_lines.append("\n")

    sm_lines = []
    for sm_name, sm in state_machines.items():
        sm_lines.append(f"  - name: {sm_name}\n")
        sm_lines.append(f"    entity: {sm['entity']}\n")
        sm_lines.append(f"    initial_state: {sm['initial_state']}\n")
        states_str = ", ".join(s['name'] for s in sm['states'])
        sm_lines.append(f"    states: [{states_str}]\n")
        sm_lines.append("\n")

    # Build actions from entities
    action_lines = []
    for e in entities:
        domain = e.table_name
        action_lines.append(f"  - name: create_{domain}\n")
        action_lines.append(f"    domain: {domain}\n")
        for f in e.fields:
            req = "(required)" if f.required else "(optional)"
            action_lines.append(f"      - {f.name} {req}\n")
        action_lines.append("\n")
        action_lines.append(f"  - name: list_{domain}s\n")
        action_lines.append(f"    domain: {domain}\n")
        action_lines.append(f"      - limit (optional, default=100)\n")
        action_lines.append("\n")

    # Constraints
    constraint_lines = []
    for e in entities:
        for f in e.fields:
            if f.required:
                constraint_lines.append(
                    f'  - name: {e.name}_{f.name}_required\n'
                    f'    entity: {e.name}\n'
                    f'    type: not_null\n'
                    f'    fields: [{f.name}]\n'
                    f'    message: "{f.name} is required"\n'
                )
        email_fields = [f for f in e.fields if "email" in f.name.lower()]
        for f in email_fields:
            constraint_lines.append(
                f'  - name: {e.name}_{f.name}_format\n'
                f'    entity: {e.name}\n'
                f'    type: check\n'
                f"    condition: \"matches \\'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{{2,}}$\\'\"\n"
                f'    message: "Invalid email format for {f.name}"\n'
            )

    tmpl = f'''# =================================================================
# AI Business Runtime — Generated runtime.yaml
# =================================================================
# Project: {name}
# Author: {author}
# =================================================================

name: {name}
description: |
  {description}
version: "1.0"
author: "{author}"

# Entry point
entry: app.main:CLI

# Standard directory layout
directories:
  app/domain/: "Entity DSL definitions (YAML)"
  app/runtime/actions/: "Business action implementations"
  app/infrastructure/: "Database models and repositories"
  data/: "SQLite database files"

# Infrastructure
infrastructure:
  database:
    type: sqlite
    path: data/{name.replace("-", "_")}.db
    auto_init: true

# Entity registry
entities:
{_indent(''.join(entity_lines), 2)}

# Actions registry
actions:
{_indent(''.join(action_lines), 2)}

# State machines
state_machines:
{_indent(''.join(sm_lines), 2)}

# Constraints
constraints:
{_indent(''.join(constraint_lines), 2)}
'''
    return tmpl.lstrip()


# ---------------------------------------------------------------------------
# app/runtime/engine.py
# ---------------------------------------------------------------------------

def engine_py(name: str, entities: list[Any]) -> str:
    """Generate app/runtime/engine.py — CRUD action handlers."""

    entity_handlers = []
    for e in entities:
        domain = e.table_name
        pascal = _to_pascal(e.name)

        handler = textwrap.dedent(f'''\
        # ---- {e.name} ----
        def _create_{domain}(params: dict) -> dict:
            """Create a new {e.name} record."""
            from app.infrastructure.models import {pascal}Model
            from sqlmodel import Session
            session = _get_session()
            record = {pascal}Model(**{{k: v for k, v in params.items() if k in [f.name for f in {e.name}._fields]}})
            session.add(record)
            session.commit()
            session.refresh(record)
            return {{"success": True, "result": record.model_dump()}}

        def _list_{domain}s(params: dict) -> dict:
            """List {e.name} records with optional filters."""
            from sqlmodel import Session, select
            from app.infrastructure.models import {pascal}Model
            session = _get_session()
            limit = params.get("limit", 100)
            query = select({pascal}Model).limit(limit)
            results = session.exec(query).all()
            return {{
                "success": True,
                "result": [r.model_dump() for r in results],
                "pagination": {{"page": 1, "per_page": limit, "total": len(results)}},
            }}

        def _get_{domain}(params: dict) -> dict:
            """Get a single {e.name} by ID."""
            from sqlmodel import Session, select
            from app.infrastructure.models import {pascal}Model
            session = _get_session()
            record = session.get({pascal}Model, params["id"])
            if not record:
                return {{"success": False, "error": "{e.name} not found"}}
            return {{"success": True, "result": record.model_dump()}}

        def _update_{domain}(params: dict) -> dict:
            """Update a {e.name} record."""
            from sqlmodel import Session
            from app.infrastructure.models import {pascal}Model
            session = _get_session()
            record = session.get({pascal}Model, params["id"])
            if not record:
                return {{"success": False, "error": "{e.name} not found"}}
            for key, value in params.items():
                if key != "id" and hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            session.refresh(record)
            return {{"success": True, "result": record.model_dump()}}

        def _delete_{domain}(params: dict) -> dict:
            """Delete a {e.name} record."""
            from sqlmodel import Session
            from app.infrastructure.models import {pascal}Model
            session = _get_session()
            record = session.get({pascal}Model, params["id"])
            if not record:
                return {{"success": False, "error": "{e.name} not found"}}
            session.delete(record)
            session.commit()
            return {{"success": True, "result": {{"deleted": params["id"]}}}}
        ''')
        entity_handlers.append(handler)

    action_map_entries = []
    for e in entities:
        domain = e.table_name
        action_map_entries.append(f'        "create_{domain}": _create_{domain},')
        action_map_entries.append(f'        "list_{domain}s": _list_{domain}s,')
        action_map_entries.append(f'        "get_{domain}": _get_{domain},')
        action_map_entries.append(f'        "update_{domain}": _update_{domain},')
        action_map_entries.append(f'        "delete_{domain}": _delete_{domain},')

    tmpl = f'''"""Business Runtime Engine — generated for: {name}"""

from __future__ import annotations
from typing import Any, Callable
from sqlmodel import create_engine, Session

# Database engine (lazy init)
_db_engine = None

def _get_engine():
    global _db_engine
    if _db_engine is None:
        from runtime.yaml import config
        db_path = config.get("infrastructure", {{}}).get("database", {{}}).get("path", "data/{{config.get("name", "runtime")}}.db")
        _db_engine = create_engine(f"sqlite:///{{db_path}}")
    return _db_engine

def _get_session() -> Session:
    return Session(_get_engine())

class RuntimeEngine:
    """Execute business actions with validation and state machine support."""

    def __init__(self):
        self.actions: dict[str, Callable] = {{}}
{chr(10).join(entity_handlers)}

        self.action_map = {{
{chr(10).join(action_map_entries)}
        }}

    def list_actions(self) -> list[str]:
        """Return all registered action names."""
        return list(self.actions.keys())

    def execute(self, action: str, params: dict | None = None) -> dict:
        """Execute an action by name."""
        params = params or {{}}
        if action not in self.action_map:
            return {{"success": False, "error": f"Unknown action: {{action}}"}}
        try:
            return self.action_map[action](params)
        except Exception as e:
            return {{"success": False, "error": str(e)}}

    def validate_constraints(self, entity: str, data: dict) -> list[str]:
        """Validate data against entity constraints. Returns list of error messages."""
        errors = []
        # TODO: load constraints from runtime.yaml
        return errors
'''
    return tmpl


# ---------------------------------------------------------------------------
# mcp_server.py
# ---------------------------------------------------------------------------

def mcp_server_py(name: str, entities: list[Any]) -> str:
    """Generate mcp_server.py — MCP server exposing engine actions as tools."""

    tool_defs = []
    tool_map_entries = []
    engine_call_entries = []

    for e in entities:
        domain = e.table_name
        tool_defs.append(textwrap.dedent(f'''\
        {{
            "name": "mcp_{domain}_list_{domain}s",
            "description": "List all {e.name} records with optional filters",
            "inputSchema": {{
                "type": "object",
                "properties": {{
                    "limit": {{"type": "integer", "description": "Max records to return", "default": 100}}
                }}
            }}
        }},
        {{
            "name": "mcp_{domain}_create_{domain}",
            "description": "Create a new {e.name} record",
            "inputSchema": {{
                "type": "object",
                "properties": {{
{_indent(_generate_field_schema(e.fields), 6)}
                }},
                "required": [{_generate_required_list(e.fields)}]
            }}
        }},
        {{
            "name": "mcp_{domain}_get_{domain}",
            "description": "Get a single {e.name} by ID",
            "inputSchema": {{
                "type": "object",
                "properties": {{
                    "id": {{"type": "string", "description": "Record ID"}}
                }},
                "required": ["id"]
            }}
        }},
        {{
            "name": "mcp_{domain}_update_{domain}",
            "description": "Update a {e.name} record",
            "inputSchema": {{
                "type": "object",
                "properties": {{
                    "id": {{"type": "string", "description": "Record ID"}},
{_indent(_generate_field_schema(e.fields, exclude=["id"]), 6)}
                }},
                "required": ["id"]
            }}
        }},
        {{
            "name": "mcp_{domain}_delete_{domain}",
            "description": "Delete a {e.name} record",
            "inputSchema": {{
                "type": "object",
                "properties": {{
                    "id": {{"type": "string", "description": "Record ID"}}
                }},
                "required": ["id"]
            }}
        }},
        '''))

        engine_call_entries.extend([
            f'        f"mcp_{domain}_list_{domain}s": lambda p: engine.execute("list_{domain}s", p),',
            f'        f"mcp_{domain}_create_{domain}": lambda p: engine.execute("create_{domain}", p),',
            f'        f"mcp_{domain}_get_{domain}": lambda p: engine.execute("get_{domain}", p),',
            f'        f"mcp_{domain}_update_{domain}": lambda p: engine.execute("update_{domain}", p),',
            f'        f"mcp_{domain}_delete_{domain}": lambda p: engine.execute("delete_{domain}", p),',
        ])

    tmpl = f'''"""MCP Server — generated for: {name}
Read README.md for deployment instructions.
"""

import sys
import json
from pathlib import Path

# Ensure project root on path
_project_root = Path(__file__).parent
sys.path.insert(0, str(_project_root))

from runtime_engine import RuntimeEngine

TOOL_DEFINITIONS = [
{chr(10).join(tool_defs)}
]

TOOL_MAP = {{
{chr(10).join(engine_call_entries)}
}}

def _jsonrpc_success(req_id, result):
    return {{"jsonrpc": "2.0", "id": req_id, "result": result}}

def _jsonrpc_error(req_id, code, message):
    return {{"jsonrpc": "2.0", "id": req_id, "error": {{"code": code, "message": message}}}}

def handle_request(req: dict) -> dict:
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return _jsonrpc_success(req_id, {{
            "protocolVersion": "2024-11-05",
            "capabilities": {{"tools": {{}}}},
            "serverInfo": {{"name": "{name}", "version": "1.0"}}
        }})

    if method == "notifications/initialized":
        return None  # No content response

    if method == "tools/list":
        return _jsonrpc_success(req_id, {{"tools": TOOL_DEFINITIONS}})

    if method == "tools/call":
        tool_name = req.get("params", {{}}).get("name", "")
        tool_args = req.get("params", {{}}).get("arguments", {{}})
        if tool_name not in TOOL_MAP:
            return _jsonrpc_error(req_id, -32601, f"Unknown tool: {{tool_name}}")
        try:
            result = TOOL_MAP[tool_name](tool_args)
            return _jsonrpc_success(req_id, {{"content": [{{"type": "text", "text": json.dumps(result)}}]}})
        except Exception as e:
            return _jsonrpc_error(req_id, -32603, str(e))

    return _jsonrpc_error(req_id, -32601, f"Unknown method: {{method}}")

def main():
    engine = RuntimeEngine()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            if resp is not None:
                print(json.dumps(resp), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({{"jsonrpc": "2.0", "error": {{"code": -32700, "message": "Parse error"}}}}), flush=True)

if __name__ == "__main__":
    main()
'''
    return tmpl


# ---------------------------------------------------------------------------
# app/infrastructure/models.py
# ---------------------------------------------------------------------------

def models_py(entities: list[Any]) -> str:
    """Generate SQLModel database models."""

    model_classes = []
    for e in entities:
        pascal = _to_pascal(e.name)

        field_lines = []
        for f in e.fields:
            annotation = {
                "string": "str",
                "text": "str",
                "integer": "int",
                "float": "float",
                "boolean": "bool",
                "datetime": "datetime",
                "date": "date",
            }.get(f.type, "str")

            extras = []
            if f.primary_key or f.name == "id":
                extras.append("primary_key=True")
            if not f.required:
                extras.append("nullable=True")
            if f.unique:
                extras.append("unique=True")
            if f.indexed:
                extras.append("index=True")
            if extras:
                field_lines.append(f"    {f.name}: {annotation} = Field({', '.join(extras)})")
            else:
                field_lines.append(f"    {f.name}: {annotation}")

        field_block = "\n".join(field_lines) if field_lines else "    pass"

        # Build class definition string without textwrap.dedent (avoids indentation issues)
        class_def = f'''class {pascal}Model(SQLModel, table=True):
    __tablename__ = "{e.table_name}"
    __table_args__ = {{"extend_existing": True}}

{field_block}
'''
        model_classes.append(class_def)

    # Remove the broken class declaration and pass statement
    tmpl = f'''"""Database models — auto-generated. Do not edit manually."""

from __future__ import annotations
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

{chr(10).join(model_classes)}
'''
    return tmpl


# ---------------------------------------------------------------------------
# app/domain/<entity>.yaml
# ---------------------------------------------------------------------------

def domain_yaml(entity) -> str:
    """Generate app/domain/<entity>.yaml DSL file."""
    field_lines = []
    for f in entity.fields:
        fl = f'      - name: {f.name}\n        type: {f.type}'
        if f.required:
            fl += '\n        required: true'
        if f.description:
            fl += f'\n        description: "{f.description}"'
        if f.unique:
            fl += '\n        unique: true'
        if f.indexed:
            fl += '\n        indexed: true'
        if f.enum_values:
            fl += f'\n        enum_values: {f.enum_values}'
        field_lines.append(fl)

    tmpl = f'''# Domain entity: {entity.name}
name: {entity.name}
table_name: {entity.table_name}
description: "{entity.description}"

fields:
{chr(10).join(field_lines)}
'''
    return tmpl


# ---------------------------------------------------------------------------
# workflows/example.yaml
# ---------------------------------------------------------------------------

def example_workflow(name: str) -> str:
    """Generate an example workflow YAML."""
    return f'''workflow:
  name: example-workflow
  version: "1.0"
  description: Example workflow for {name}

tasks:
  - id: step_1
    type: prompt
    config:
      prompt: "Hello! What is 2 + 2?"
      model: gpt-4o
      max_tokens: 50
'''


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _indent(text: str, spaces: int) -> str:
    """Indent every line of text by `spaces` spaces."""
    prefix = " " * spaces
    return "\n".join(prefix + line if line else "" for line in text.split("\n"))


def _to_pascal(name: str) -> str:
    """Convert snake_case or any string to PascalCase."""
    return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))


def _to_snake(name: str) -> str:
    """Convert PascalCase to snake_case."""
    import re
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _generate_field_schema(fields, exclude=None) -> str:
    """Generate JSON Schema properties for fields."""
    exclude = exclude or []
    lines = []
    for f in fields:
        if f.name in exclude:
            continue
        schema = f'                "{f.name}": {{"type": "{_js_type(f.type)}", "description": "{f.description or f.name}"}}'
        lines.append(schema)
    return ",\n".join(lines) if lines else '                "id": {"type": "string", "description": "Record ID"}'


def _generate_required_list(fields) -> str:
    required = [f.name for f in fields if f.required and f.name != "id"]
    if not required:
        required = ["id"]
    return ", ".join(f'"{r}"' for r in required)


def _js_type(field_type: str) -> str:
    """Map field type to JSON Schema type."""
    return {
        "string": "string",
        "text": "string",
        "integer": "integer",
        "float": "number",
        "boolean": "boolean",
        "datetime": "string",
        "date": "string",
        "enum": "string",
    }.get(field_type, "string")
