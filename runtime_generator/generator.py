"""Core generator logic for AI Business Runtime Framework."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime_generator.templates import (
    runtime_yaml,
    engine_py,
    mcp_server_py,
    models_py,
    domain_yaml,
    example_workflow_yaml as example_workflow,
    ai_prompt_md,
)


# --------------------------------------------------------------------------]
# Constraint system
# ---------------------------------------------------------------------------

@dataclass
class ConstraintDef:
    """Declarative business constraint attached to an entity.

    These constraints are the SINGLE SOURCE OF TRUTH for:
    1. Data validation in engine.py handlers (auto-generated)
    2. AI-readable tool descriptions (auto-generated)
    3. MCP inputSchema annotations (auto-generated)

    When a user adds a constraint to an entity YAML, it automatically:
    - Updates validation logic in the generated CRUD handlers
    - Updates the AI prompt documentation
    - Updates MCP tool descriptions with business semantics
    """

    # Which constraint type
    type: str  # required_if | unique | unique_together | valid_transition | custom | min_length | max_length

    # Which field(s) this constraint applies to
    fields: list[str]

    # Human-readable explanation for AI agents
    # This is the MOST IMPORTANT field — it tells the AI WHY this constraint exists
    # and how to handle it.
    # Example: "An email address must be unique across all leads to prevent duplicates"
    explanation: str = ""

    # Additional parameters per type
    # required_if: {"when_field": "source", "when_value": "cold_call"}
    # valid_transition: {"from": [...], "to": [...]}
    # custom: {"python": "lambda ctx: ctx.get('status') != 'cancelled'"}
    params: dict[str, Any] = field(default_factory=dict)

    # Severity: error (block write) | warning (log but allow)
    severity: str = "error"

    def to_python_validation(self) -> str:
        """Generate Python validation code for this constraint."""
        if self.type == "required_if":
            when_field = self.params.get("when_field", "")
            when_value = self.params.get("when_value", "")
            fname = self.fields[0]
            return (
                f"if params.get('{when_field}') == '{when_value}'"
                f" and not params.get('{fname}'):\n"
                f"    errors.append('{fname} is required when {when_field}={when_value}')"
            )
        elif self.type == "unique":
            fname = self.fields[0]
            return (
                f"# unique check: {fname}\n"
                f"session.get({self._model_name()}, params.get('{fname}'))"
            )
        elif self.type == "unique_together":
            field_list = ", ".join(f"params.get('{f}')" for f in self.fields)
            parts = " ".join(
                f"{self._model_name()}.{f} == {f}" for f in self.fields
            )
            return (
                f"session.exec(select({self._model_name()}).where(and_({parts}))).first()"
            )
        elif self.type == "min_length":
            f = self.fields[0]
            min_v = self.params.get("value", 0)
            return (
                f"if params.get('{f}') and len(params.get('{f}', '')) < {min_v}:\n"
                f"    errors.append('{f} must be at least {min_v} characters')"
            )
        elif self.type == "max_length":
            f = self.fields[0]
            max_v = self.params.get("value", 0)
            return (
                f"if params.get('{f}') and len(params.get('{f}', '')) > {max_v}:\n"
                f"    errors.append('{f} must be at most {max_v} characters')"
            )
        elif self.type == "valid_transition":
            to_states = self.params.get("to", [])
            field = self.fields[0]
            allowed = ", ".join(f"'{s}'" for s in to_states)
            return (
                f"current = params.get('{field}', '')\n"
                f"allowed = [{allowed}]\n"
                f"if current and current not in allowed:\n"
                f"    errors.append('{field} transition not allowed. Must be one of: ' + str(allowed))"
            )
        elif self.type == "custom":
            expr = self.params.get("python", "True")
            return f"if not ({expr}):\n    errors.append('{self.explanation}')"
        return ""

    def to_ai_description(self) -> str:
        """Human + AI readable explanation of this constraint."""
        if self.type == "required_if":
            wf = self.params.get("when_field", "")
            wv = self.params.get("when_value", "")
            return (
                f"**Required when [{wf}] is [{wv}]**: "
                f"{self.explanation or f'{self.fields[0]} must be provided when {wf} is {wv}'}"
            )
        elif self.type == "unique":
            return (
                f"**Unique**: {self.explanation or f'{self.fields[0]} must be unique across all records'}"
            )
        elif self.type == "unique_together":
            fields_str = ", ".join(self.fields)
            return (
                f"**Unique together [{fields_str}]**: "
                f"{self.explanation or f'The combination of {fields_str} must be unique'}"
            )
        elif self.type == "valid_transition":
            return (
                f"**State transition**: {self.explanation or f'{self.fields[0]} can only transition to allowed states'}"
            )
        elif self.type == "min_length":
            v = self.params.get("value", 0)
            return f"**Min length [{self.fields[0]}]**: {self.explanation or f'{self.fields[0]} must be at least {v} characters'}"
        elif self.type == "max_length":
            v = self.params.get("value", 0)
            return f"**Max length [{self.fields[0]}]**: {self.explanation or f'{self.fields[0]} must be at most {v} characters'}"
        elif self.type == "custom":
            return f"**Rule**: {self.explanation}"
        return self.explanation

    def _model_name(self) -> str:
        return "TODO_Model"  # overridden in generator context


@dataclass
class FieldDef:
    """Represents a single field in an entity."""

    name: str
    type: str  # string, integer, float, boolean, datetime, date, text, enum
    required: bool = False
    primary_key: bool = False
    description: str = ""
    default: Any = None
    unique: bool = False
    indexed: bool = False
    enum_values: list[str] | None = None
    min_length: int | None = None
    max_length: int | None = None


@dataclass
class EntityDef:
    """Represents a domain entity.

    This is the central data structure. Changes here cascade to:
    - SQLModel table (models.py)
    - CRUD engine (engine.py)
    - MCP tool definitions (mcp_server.py)
    - AI prompt documentation (ai_prompt.md)
    - Domain schema (domains/{entity}.yaml)

    All AI-facing descriptions should be filled in (description fields)
    to help AI agents understand the business semantics.
    """

    name: str
    table_name: str
    description: str = ""
    # AI-friendly description: explains what this entity represents in business terms
    # e.g., "A qualified sales prospect who has shown interest in our products"
    business_meaning: str = ""
    fields: list[FieldDef] = field(default_factory=list)
    state_machine: dict[str, Any] | None = None
    # Declarative constraints — see ConstraintDef
    constraints: list[ConstraintDef] = field(default_factory=list)

    def get_field(self, name: str) -> FieldDef | None:
        return next((f for f in self.fields if f.name == name), None)

    def get_constraint(self, constraint_type: str) -> list[ConstraintDef]:
        return [c for c in self.constraints if c.type == constraint_type]


@dataclass
class RelationDef:
    """Represents a relationship between entities."""

    name: str
    type: str  # one_to_many, many_to_one, one_to_one, many_to_many
    source_entity: str
    target_entity: str
    description: str = ""


@dataclass
class GeneratorConfig:
    """Configuration for runtime generation."""

    name: str = "my-runtime"
    output_dir: Path = Path.cwd()
    include_examples: bool = True
    author: str = ""
    description: str = ""


class RuntimeGenerator:
    """Generate a complete business runtime from structured input."""

    def __init__(self, config: GeneratorConfig | str) -> None:
        if isinstance(config, str):
            raise TypeError(
                f"RuntimeGenerator expects a GeneratorConfig instance, got str: {config!r}. "
                "Did you pass a project name instead of a GeneratorConfig? "
                "Use GeneratorConfig(name='...') to construct."
            )
        self.config = config
        self.entities: list[EntityDef] = []
        self.relations: list[RelationDef] = []
        self.state_machines: dict[str, dict[str, Any]] = {}

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def add_entity(self, entity: EntityDef) -> None:
        """Register an entity."""
        self.entities.append(entity)

    def add_relation(self, relation: RelationDef) -> None:
        """Register a relationship."""
        self.relations.append(relation)

    def set_state_machine(self, entity_name: str, sm: dict[str, Any]) -> None:
        """Set state machine for an entity."""
        self.state_machines[entity_name] = sm

    def save(self) -> Path:
        """Generate and save all runtime files to output_dir."""
        out = self.config.output_dir / self.config.name
        out.mkdir(parents=True, exist_ok=True)

        self._write_runtime_yaml(out)
        self._write_engine_py(out)
        self._write_mcp_server_py(out)
        self._write_models_py(out)
        self._write_domain_files(out)
        self._write_ai_prompt(out)

        if self.config.include_examples:
            self._write_example_workflow(out)

        return out

    # -------------------------------------------------------------------------
    # Private: file writers
    # -------------------------------------------------------------------------

    def _write_runtime_yaml(self, out: Path) -> None:
        content = runtime_yaml(
            name=self.config.name,
            description=self.config.description,
            author=self.config.author,
            entities=self.entities,
            state_machines=self.state_machines,
        )
        (out / "runtime.yaml").write_text(content, encoding="utf-8")

    def _write_engine_py(self, out: Path) -> None:
        content = engine_py(
            name=self.config.name,
            entities=self.entities,
        )
        (out / "app" / "runtime").mkdir(parents=True, exist_ok=True)
        (out / "app" / "runtime" / "engine.py").write_text(content, encoding="utf-8")

    def _write_mcp_server_py(self, out: Path) -> None:
        content = mcp_server_py(
            name=self.config.name,
            entities=self.entities,
        )
        (out / "mcp_server.py").write_text(content, encoding="utf-8")

    def _write_models_py(self, out: Path) -> None:
        content = models_py(entities=self.entities)
        (out / "app" / "infrastructure").mkdir(parents=True, exist_ok=True)
        (out / "app" / "infrastructure" / "models.py").write_text(content, encoding="utf-8")

    def _write_domain_files(self, out: Path) -> None:
        for entity in self.entities:
            content = domain_yaml(entity=entity)
            path = out / "app" / "domain" / f"{entity.table_name}.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def _write_example_workflow(self, out: Path) -> None:
        content = example_workflow(name=self.config.name, entities=list(self.entities))
        workflows_dir = out / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        (workflows_dir / "example.yaml").write_text(content, encoding="utf-8")

    def _write_ai_prompt(self, out: Path) -> None:
        """Generate AI-readable prompt documenting all actions and constraints."""
        content = ai_prompt_md(
            name=self.config.name,
            description=self.config.description,
            entities=self.entities,
        )
        (out / "AI.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def build_generator(config: GeneratorConfig, answers: dict[str, Any]) -> RuntimeGenerator:
    """Build a RuntimeGenerator from the interactive wizard answers dict."""

    gen = RuntimeGenerator(config)

    # Entity definitions from wizard
    for entity_data in answers.get("entities", []):
        entity = EntityDef(
            name=entity_data["name"],
            table_name=entity_data.get("table_name", _to_snake(entity_data["name"])),
            description=entity_data.get("description", ""),
            business_meaning=entity_data.get("business_meaning", ""),
            fields=[
                FieldDef(
                    name=f["name"],
                    type=f.get("type", "string"),
                    required=f.get("required", False),
                    primary_key=f.get("primary_key", f.get("name") == "id"),
                    description=f.get("description", ""),
                    enum_values=f.get("enum_values"),
                    unique=f.get("unique", False),
                    indexed=f.get("indexed", False),
                    default=f.get("default"),
                    min_length=f.get("min_length"),
                    max_length=f.get("max_length"),
                )
                for f in entity_data.get("fields", [])
            ],
            constraints=[
                ConstraintDef(
                    type=c.get("type", "required_if"),
                    fields=c.get("fields", []),
                    explanation=c.get("explanation", ""),
                    params=c.get("params", {}),
                    severity=c.get("severity", "error"),
                )
                for c in entity_data.get("constraints", [])
            ],
        )

        # Attach state machine if defined
        if entity_data.get("state_machine"):
            entity.state_machine = entity_data["state_machine"]
            gen.set_state_machine(entity.name, entity_data["state_machine"])

        gen.add_entity(entity)

    # Relations
    for rel_data in answers.get("relations", []):
        gen.add_relation(
            RelationDef(
                name=rel_data["name"],
                type=rel_data.get("type", "one_to_many"),
                source_entity=rel_data["source_entity"],
                target_entity=rel_data["target_entity"],
                description=rel_data.get("description", ""),
            )
        )

    return gen


def _to_snake(name: str) -> str:
    """Convert PascalCase to snake_case."""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
