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
)


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
    """Represents a domain entity."""

    name: str
    table_name: str
    description: str = ""
    fields: list[FieldDef] = field(default_factory=list)
    state_machine: dict[str, Any] | None = None


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


# Convenience factory to build a complete generator from user answers
def build_generator(config: GeneratorConfig, answers: dict[str, Any]) -> RuntimeGenerator:
    """Build a RuntimeGenerator from the interactive wizard answers dict."""

    gen = RuntimeGenerator(config)

    # Entity definitions from wizard
    for entity_data in answers.get("entities", []):
        entity = EntityDef(
            name=entity_data["name"],
            table_name=entity_data.get("table_name", _to_snake(entity_data["name"])),
            description=entity_data.get("description", ""),
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
                )
                for f in entity_data.get("fields", [])
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
