"""Interactive wizard prompts for building a business runtime data model.

Uses stdin for CLI interaction. Returns a structured answers dict
suitable for build_generator().
"""

from __future__ import annotations

import re
import sys
from runtime_generator.generator import build_generator, FieldDef, GeneratorConfig


# ---------------------------------------------------------------------------
# Field type mapping
# ---------------------------------------------------------------------------

FIELD_TYPES = [
    ("string", "Short text (e.g. name, email)"),
    ("text", "Long text (e.g. description, notes)"),
    ("integer", "Whole number (e.g. age, quantity)"),
    ("float", "Decimal number (e.g. price, weight)"),
    ("boolean", "True/False flag"),
    ("datetime", "Date and time"),
    ("date", "Date only"),
    ("enum", "One of a fixed list of values"),
]


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_header(title: str) -> None:
    lines = len(title) + 4
    print(f"\n{'=' * (lines if lines < 72 else 72)}")
    print(f"  {title}")
    print(f"{'=' * (lines if lines < 72 else 72)}\n")


def _print_step(step: int, total: int, title: str) -> None:
    print(f"\n[Step {step}/{total}] {title}\n")


def _ask(prompt: str, default: str = "") -> str:
    """Ask a question, return user input (or default)."""
    suffix = f" [{default}]" if default else ""
    raw = input(f"  {prompt}{suffix}: ").strip()
    return raw if raw else default


def _ask_choice(prompt: str, options: list[str], default: str) -> str:
    """Present numbered choices, return selected option."""
    print(f"  {prompt}")
    for i, opt in enumerate(options, 1):
        marker = " (default)" if opt == default else ""
        print(f"    {i}. {opt}{marker}")
    while True:
        raw = input(f"  Enter choice [1-{len(options)}]: ").strip()
        if not raw:
            return default
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print(f"  Invalid choice. Enter 1-{len(options)}.")


def _ask_yesno(prompt: str, default: bool) -> bool:
    """Ask a yes/no question."""
    suffix = " [Y/n]" if default else " [y/N]"
    raw = input(f"  {prompt}{suffix}: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def _ask_multi(prompt: str, min_count: int = 0) -> list[str]:
    """Ask for comma-separated list, return list of non-empty strings."""
    print(f"  {prompt} (comma-separated, enter empty to finish)")
    items: list[str] = []
    while True:
        raw = input(f"    Item (or Enter to finish): ").strip()
        if not raw:
            if len(items) >= min_count:
                break
            print(f"    At least {min_count} item(s) required.")
            continue
        for part in [p.strip() for p in raw.split(",")]:
            if part:
                items.append(part)
        print(f"    Current list: {', '.join(items)}")
    return items


def _validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


# ---------------------------------------------------------------------------
# Wizard steps
# ---------------------------------------------------------------------------

def run_wizard() -> dict:
    """Run the full interactive wizard. Returns an answers dict."""

    _print_header("AI Business Runtime — Project Setup Wizard")

    print("This wizard will ask you 5 questions to configure your runtime.")
    print("Press Enter to accept the default value shown in brackets.\n")

    # Step 1: Project basics
    _print_step(1, 5, "Project Basics")
    project_name = _ask("Project name", "my-trade-runtime")
    project_author = _ask("Author / Company name", "")
    project_description = _ask("Brief project description", "AI-powered business runtime")
    include_examples = _ask_yesno("Include example workflow files", True)

    # Step 2: Entities
    _print_step(2, 5, "Data Modeling — Entities")
    print("  Entities are the core data types in your business (e.g. Lead, Customer, Order).")
    n_entities = _ask("How many entities do you need", "2")
    try:
        n = max(1, int(n_entities))
    except ValueError:
        n = 2

    entities = []
    for i in range(n):
        print(f"\n  --- Entity {i + 1} of {n} ---")
        entity_name = _ask(f"  Entity name (e.g. Lead, Customer)", f"Entity{i+1}")
        entity = _collect_entity_fields(entity_name)
        entities.append(entity)

    # Step 3: Relations
    _print_step(3, 5, "Data Modeling — Relations")
    if _ask_yesno("Do you want to define relationships between entities", False):
        relations = _collect_relations(entities)
    else:
        relations = []

    # Step 4: State machines
    _print_step(4, 5, "Business Logic — State Machines")
    print("  State machines define lifecycle stages for an entity.")
    print("  Example: Lead → Contacted → Qualified → Customer")
    state_machines: list[dict] = []
    for entity in entities:
        if _ask_yesno(f"Define a lifecycle for {entity['name']}", False):
            sm = _collect_state_machine(entity["name"])
            if sm:
                state_machines.append(sm)

    # Step 5: Business constraints
    _print_step(5, 5, "Business Rules — Constraints")
    print("  Constraints validate data before it's saved (e.g. email format, required fields).")
    constraints: list[dict] = []
    for entity in entities:
        if _ask_yesno(f"Add validation rules for {entity['name']}", False):
            entity_constraints = _collect_constraints(entity["name"], entity["fields"])
            constraints.extend(entity_constraints)

    answers = {
        "name": project_name,
        "author": project_author,
        "description": project_description,
        "include_examples": include_examples,
        "entities": entities,
        "relations": relations,
        "state_machines": state_machines,
        "constraints": constraints,
    }

    _print_summary(answers)
    return answers


def _collect_entity_fields(entity_name: str) -> dict:
    """Collect fields for one entity."""
    print(f"\n  Defining fields for: {entity_name}")
    table_name = _ask("  Database table name", _to_snake(entity_name))
    description = _ask("  Description (optional)", "")

    print(f"\n  Adding fields to '{entity_name}' — press Enter on empty field name to finish")
    fields: list[dict] = []

    # Auto-add id primary key
    fields.append({
        "name": "id",
        "type": "string",
        "required": True,
        "primary_key": True,
        "description": "Unique identifier",
        "unique": True,
    })

    while True:
        fname = input("\n  Field name (Enter to finish adding fields): ").strip()
        if not fname:
            break

        # Select field type
        print(f"  Field type for '{fname}':")
        for i, (ftype, fdesc) in enumerate(FIELD_TYPES, 1):
            print(f"    {i}. {ftype} — {fdesc}")
        ftype_raw = input(f"  Enter type [1-{len(FIELD_TYPES)}]: ").strip()
        try:
            ftype_idx = int(ftype_raw) - 1
            ftype = FIELD_TYPES[ftype_idx][0] if 0 <= ftype_idx < len(FIELD_TYPES) else "string"
        except ValueError:
            ftype = "string"

        required = _ask_yesno("Is this field required", False)
        unique = _ask_yesno("Should values be unique", False) if ftype in ("string", "integer") else False
        indexed = _ask_yesno("Index this field for fast lookup", False) if not unique else True
        fdesc = _ask("Field description (optional)", "")

        field_data: dict = {
            "name": fname,
            "type": ftype,
            "required": required,
            "unique": unique,
            "indexed": indexed,
            "description": fdesc,
        }

        if ftype == "enum":
            enum_vals = _ask_multi("  Enum values (e.g. active,inactive,pending)")
            field_data["enum_values"] = enum_vals

        if ftype == "string" and not unique:
            maxlen = _ask("  Max character length (Enter to skip)", "")
            if maxlen.isdigit():
                field_data["max_length"] = int(maxlen)

        fields.append(field_data)

    return {
        "name": entity_name,
        "table_name": table_name,
        "description": description,
        "fields": fields,
    }


def _collect_relations(entities: list[dict]) -> list[dict]:
    """Collect entity relationships."""
    print("\n  Defining entity relationships")
    RELATION_TYPES = ["one_to_many", "many_to_one", "one_to_one", "many_to_many"]
    RELATION_PROMPTS = {
        "one_to_many": "A → many (e.g. Customer has many Orders)",
        "many_to_one": "Many → A (e.g. Order belongs to Customer)",
        "one_to_one": "A ↔ one (e.g. User has one Profile)",
        "many_to_many": "Many ↔ many (e.g. Students ↔ Courses)",
    }

    entity_names = [e["name"] for e in entities]
    relations: list[dict] = []
    done = False
    while not done:
        print(f"\n  Available entities: {', '.join(entity_names)}")
        print(f"  Available relation types:")
        for rtype, rdesc in RELATION_PROMPTS.items():
            print(f"    - {rtype}: {rdesc}")

        source = _ask("Source entity (one end)", entity_names[0] if entity_names else "")
        target = _ask("Target entity (many end)", entity_names[-1] if len(entity_names) > 1 else "")
        rtype = _ask_choice("Relation type", RELATION_TYPES, "one_to_many")
        rdesc = _ask("Relationship description (optional)", "")

        relations.append({
            "name": f"{source}_to_{target}",
            "type": rtype,
            "source_entity": source,
            "target_entity": target,
            "description": rdesc,
        })

        done = not _ask_yesno("Add another relationship", False)

    return relations


def _collect_state_machine(entity_name: str) -> dict | None:
    """Collect state machine definition for an entity."""
    print(f"\n  Defining state machine for '{entity_name}'")
    initial_state = _ask("Initial state name", "new")
    states_raw = _ask_multi("State names (e.g. new, active, closed)", min_count=2)
    if len(states_raw) < 2:
        print("  State machine needs at least 2 states. Skipping.")
        return None

    states = []
    for sname in states_raw:
        is_final = _ask_yesno(f"  Is '{sname}' a final/terminal state", False)
        states.append({
            "name": sname,
            "type": "final" if is_final else "normal",
            "is_final": is_final,
        })

    print("\n  Transitions: define how entities move between states")
    transitions: list[dict] = []
    done = False
    while not done:
        from_state = _ask("From state")
        to_state = _ask("To state")
        event = _ask("Event that triggers this transition (optional)", "")
        condition = _ask("Condition (optional)", "")

        transitions.append({
            "name": f"{from_state}_to_{to_state}",
            "from_state": from_state,
            "to_state": to_state,
            "event": event,
            "condition": condition,
        })

        done = not _ask_yesno("Add another transition", False)

    return {
        "name": f"{entity_name}_lifecycle",
        "entity": entity_name,
        "initial_state": initial_state,
        "states": states,
        "transitions": transitions,
    }


def _collect_constraints(entity_name: str, fields: list[dict]) -> list[dict]:
    """Collect validation constraints for an entity."""
    constraints: list[dict] = []
    field_names = [f["name"] for f in fields]

    print(f"\n  Adding validation rules for '{entity_name}'")

    # Required fields
    required_fields = [f["name"] for f in fields if f.get("required")]
    if required_fields:
        constraints.append({
            "name": f"{entity_name}_required_fields",
            "entity": entity_name,
            "type": "not_null",
            "fields": required_fields,
            "message": f"Required fields cannot be empty: {', '.join(required_fields)}",
        })

    # Unique fields
    unique_fields = [f["name"] for f in fields if f.get("unique")]
    if unique_fields:
        constraints.append({
            "name": f"{entity_name}_unique_fields",
            "entity": entity_name,
            "type": "unique",
            "fields": unique_fields,
            "message": f"Fields must be unique: {', '.join(unique_fields)}",
        })

    # Email field
    email_candidates = [f for f in fields if "email" in f["name"].lower()]
    if email_candidates:
        constraints.append({
            "name": f"{entity_name}_email_format",
            "entity": entity_name,
            "type": "check",
            "fields": [email_candidates[0]["name"]],
            "condition": f"matches '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'",
            "message": f"Invalid email format for {email_candidates[0]['name']}",
        })

    # Max length
    for f in fields:
        if f.get("max_length"):
            constraints.append({
                "name": f"{entity_name}_{f['name']}_max_length",
                "entity": entity_name,
                "type": "check",
                "fields": [f["name"]],
                "condition": f"length <= {f['max_length']}",
                "message": f"{f['name']} exceeds maximum length of {f['max_length']}",
            })

    if constraints:
        print(f"  Auto-generated {len(constraints)} constraint(s)")

    return constraints


def _print_summary(answers: dict) -> None:
    """Print a summary of the wizard answers."""
    _print_header("Setup Summary")

    print(f"  Project name : {answers['name']}")
    print(f"  Author       : {answers['author'] or '(not set)'}")
    print(f"  Description  : {answers['description']}")
    print(f"  Examples     : {'Yes' if answers['include_examples'] else 'No'}")

    print(f"\n  Entities ({len(answers['entities'])}):")
    for e in answers["entities"]:
        print(f"    - {e['name']} (table: {e['table_name']}, {len(e['fields'])} fields)")

    if answers.get("relations"):
        print(f"\n  Relations ({len(answers['relations'])}):")
        for r in answers["relations"]:
            print(f"    - {r['type']}: {r['source_entity']} → {r['target_entity']}")

    if answers.get("state_machines"):
        print(f"\n  State Machines ({len(answers['state_machines'])}):")
        for sm in answers["state_machines"]:
            print(f"    - {sm['name']} ({sm['entity']}): {len(sm['states'])} states, {len(sm['transitions'])} transitions")

    if answers.get("constraints"):
        print(f"\n  Constraints: {len(answers['constraints'])} rule(s) auto-generated")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _to_snake(name: str) -> str:
    """Convert PascalCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entry point for the wizard."""
    try:
        answers = run_wizard()
        config = GeneratorConfig(
            name=answers["name"],
            output_dir=Path.cwd(),
            include_examples=answers["include_examples"],
            author=answers["author"],
            description=answers["description"],
        )
        from runtime_generator.generator import RuntimeGenerator

        gen = build_generator(config, answers)
        out_path = gen.save()

        print(f"\n{'=' * 50}")
        print(f"  Runtime project generated successfully!")
        print(f"  Location: {out_path}")
        print(f"\n  Next steps:")
        print(f"    cd {out_path}")
        print(f"    ai-runtime generate")
        print(f"    ai-runtime run")
        print(f"{'=' * 50}\n")
        return 0
    except KeyboardInterrupt:
        print("\n\nAborted.")
        return 1
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
