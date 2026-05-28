"""Interactive requirements planning — collect entity definitions before generation.

This is the SEPARATE PLAN phase. Run this FIRST when a user says
"帮我生成 XX 系统" to collect requirements before any code is generated.

Usage:
    python -m cli.main plan [--output entities.yaml]

Workflow:
    1. Run: python -m cli.main plan
    2. AI asks the user questions about entities, fields, constraints
    3. Generate entities.yaml
    4. User confirms → then run: python -m cli.main generate --config entities.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def ask_system_name() -> str:
    """Ask for the system/project name."""
    print("\n" + "=" * 60)
    print("  AI Business Runtime — Requirements Planner")
    print("=" * 60)
    print()
    name = input("📛 系统名称（英文，用于代码，如 OrderSystem）: ").strip()
    while not name:
        print("  ⚠️  请输入系统名称")
        name = input("📛 系统名称（英文）: ").strip()
    return name


def ask_description() -> str:
    """Ask for a brief system description."""
    desc = input("📝 系统描述（可选，回车跳过）: ").strip()
    return desc


def ask_author() -> str:
    """Ask for the author."""
    author = input("👤 作者/用户名称（可选，回车跳过）: ").strip()
    return author


def ask_entity_list() -> list[str]:
    """Ask for the list of entities."""
    print("\n" + "-" * 40)
    print("  实体（Entity）定义")
    print("-" * 40)
    print("  实体 = 数据表，如：Lead（线索）、Order（订单）、Product（产品）")
    print()

    entities = []
    while True:
        entity = input("  ➕ 添加实体（直接回车结束添加）: ").strip()
        if not entity:
            break
        entities.append(entity)
        print(f"    ✓ 已添加: {entity}")

    if not entities:
        print("  ⚠️  至少需要一个实体")
        return ask_entity_list()

    return entities


def ask_fields_for_entity(entity_name: str) -> list[dict]:
    """Ask for fields of a given entity."""
    print(f"\n  ── {entity_name} 的字段 ──")
    print(f"  输入格式: 字段名, 类型, 是否必填")
    print(f"  类型选项: string | text | integer | float | boolean | datetime | enum")
    print(f"  示例: name, string, yes")
    print(f"  枚举类型示例: status, enum[new|contacted|qualified|lost], yes")
    print()

    fields = []
    while True:
        line = input(f"  ➕ 添加字段（直接回车结束）: ").strip()
        if not line:
            break

        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            print("  ⚠️  格式: 字段名, 类型, 是否必填(yes/no)")
            continue

        fname, ftype, required = parts[0], parts[1].lower(), parts[2].lower()
        required_bool = required in ("yes", "y", "true", "是")

        field: dict[str, object] = {
            "name": fname,
            "type": ftype,
            "required": required_bool,
            "description": parts[3] if len(parts) > 3 else "",
        }

        # Handle enum type
        if ftype.startswith("enum"):
            # enum[new|contacted|qualified|lost]
            enum_content = ftype[5:-1]  # strip "enum[" and "]"
            values = [v.strip() for v in enum_content.split("|")]
            field["type"] = "enum"
            field["enum_values"] = values

        fields.append(field)
        print(f"    ✓ {fname} ({ftype})" + (" [必填]" if required_bool else ""))

    return fields


def ask_constraints_for_entity(entity_name: str, fields: list[dict]) -> list[dict]:
    """Ask for constraints on an entity."""
    print(f"\n  ── {entity_name} 的业务约束（可选）──")
    print(f"  约束类型:")
    print(f"    1. unique        — 字段值全局唯一（如邮箱）")
    print(f"    2. required_if   — 条件必填（如来源=cold_call时必填电话）")
    print(f"    3. valid_transition — 状态转换路径（如 new→contacted→qualified）")
    print(f"    4. min_length    — 字符串最短长度")
    print(f"    5. max_length    — 字符串最长长度")
    print(f"    6. custom       — 自定义 Python 表达式")
    print()

    field_names = [f["name"] for f in fields]
    constraints = []

    while True:
        ctype = input("  ➕ 添加约束（1-6，或直接回车结束）: ").strip()
        if not ctype:
            break

        if ctype not in ("1", "2", "3", "4", "5", "6"):
            print("  ⚠️  请输入 1-6")
            continue

        constraint_map = {
            "1": "unique",
            "2": "required_if",
            "3": "valid_transition",
            "4": "min_length",
            "5": "max_length",
            "6": "custom",
        }
        ctype_name = constraint_map[ctype]

        if ctype_name == "unique":
            print(f"  可选字段: {', '.join(field_names)}")
            fname = input("  字段名: ").strip()
            explanation = input("  说明（如: 邮箱必须唯一）: ").strip()
            constraints.append({
                "type": "unique",
                "fields": [fname],
                "explanation": explanation,
            })

        elif ctype_name == "required_if":
            print(f"  可选字段: {', '.join(field_names)}")
            fname = input("  字段名: ").strip()
            when_field = input("  条件字段名: ").strip()
            when_value = input(f"  条件字段值（如 {fname} 的触发值）: ").strip()
            explanation = input("  说明: ").strip()
            constraints.append({
                "type": "required_if",
                "fields": [fname],
                "explanation": explanation,
                "params": {"when_field": when_field, "when_value": when_value},
            })

        elif ctype_name == "valid_transition":
            print(f"  可选字段: {', '.join(field_names)}")
            fname = input("  状态字段名: ").strip()
            states = input("  可用状态（用 | 分隔，如 new|contacted|qualified）: ").strip()
            states_list = [s.strip() for s in states.split("|")]
            explanation = input("  说明（如: 状态只能向前推进）: ").strip()
            constraints.append({
                "type": "valid_transition",
                "fields": [fname],
                "explanation": explanation,
                "params": {"values": states_list},
            })

        elif ctype_name == "min_length":
            print(f"  可选字段: {', '.join(field_names)}")
            fname = input("  字段名: ").strip()
            min_v = input("  最短长度: ").strip()
            explanation = input("  说明: ").strip()
            constraints.append({
                "type": "min_length",
                "fields": [fname],
                "explanation": explanation,
                "params": {"value": int(min_v)},
            })

        elif ctype_name == "max_length":
            print(f"  可选字段: {', '.join(field_names)}")
            fname = input("  字段名: ").strip()
            max_v = input("  最长长度: ").strip()
            explanation = input("  说明: ").strip()
            constraints.append({
                "type": "max_length",
                "fields": [fname],
                "explanation": explanation,
                "params": {"value": int(max_v)},
            })

        elif ctype_name == "custom":
            fname = input(f"  字段名（多个用逗号分隔）: ").strip()
            fields_list = [f.strip() for f in fname.split(",")]
            expression = input("  Python 表达式（如: ctx['status'] != 'cancelled'）: ").strip()
            explanation = input("  说明: ").strip()
            constraints.append({
                "type": "custom",
                "fields": fields_list,
                "explanation": explanation,
                "params": {"python": expression},
            })

        print(f"    ✓ 已添加约束: {ctype_name}")

    return constraints


def ask_more_entities() -> bool:
    """Ask if user wants to add more entities."""
    again = input("\n  ➕ 继续添加新实体？ (yes/no，回车=no）: ").strip().lower()
    return again in ("yes", "y", "是")


# ---------------------------------------------------------------------------
# YAML building
# ---------------------------------------------------------------------------

def to_snake(name: str) -> str:
    """Convert PascalCase to snake_case."""
    import re
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def build_yaml(
    name: str,
    description: str,
    author: str,
    entities: list[dict],
) -> str:
    """Build entities.yaml content."""
    lines = [
        f"# entities.yaml — {name}",
        f"# Generated by: python -m cli.main plan",
        f"# DO NOT edit generated files directly — modify this YAML and regenerate",
        "",
        f"name: {name}",
        f"description: {description}",
        f"author: {author}",
        "",
        "entities:",
    ]

    for entity in entities:
        lines.append(f"  - name: {entity['name']}")
        lines.append(f"    table_name: {to_snake(entity['name'])}")
        if entity.get("description"):
            lines.append(f"    description: {entity['description']}")
        if entity.get("business_meaning"):
            lines.append(f"    business_meaning: {entity['business_meaning']}")
        lines.append(f"    fields:")

        for field in entity["fields"]:
            lines.append(f"      - name: {field['name']}")
            lines.append(f"        type: {field['type']}")
            if field.get("required"):
                lines.append(f"        required: true")
            if field.get("primary_key"):
                lines.append(f"        primary_key: true")
            if field.get("unique"):
                lines.append(f"        unique: true")
            if field.get("description"):
                lines.append(f"        description: \"{field['description']}\"")
            if field.get("enum_values"):
                lines.append(f"        enum_values:")
                for v in field["enum_values"]:
                    lines.append(f"          - {v}")

        if entity.get("constraints"):
            lines.append(f"    constraints:")
            for constraint in entity["constraints"]:
                lines.append(f"      - type: {constraint['type']}")
                lines.append(f"        fields: [{', '.join(constraint['fields'])}]")
                if constraint.get("explanation"):
                    lines.append(f"        explanation: \"{constraint['explanation']}\"")
                if constraint.get("params"):
                    for pk, pv in constraint["params"].items():
                        if isinstance(pv, list):
                            lines.append(f"        params:")
                            lines.append(f"          {pk}:")
                            for item in pv:
                                lines.append(f"            - {item}")
                        else:
                            lines.append(f"        params:")
                            lines.append(f"          {pk}: {pv}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Summary & confirmation
# ---------------------------------------------------------------------------

def print_summary(name: str, entities: list[dict]) -> None:
    """Print a summary of what will be generated."""
    print("\n" + "=" * 60)
    print("  📋 需求摘要 — 请确认")
    print("=" * 60)
    print(f"\n  系统名称: {name}")
    print(f"  实体数量: {len(entities)}")
    print()

    for entity in entities:
        print(f"  ┌─ {entity['name']}")
        for field in entity["fields"]:
            req = " [必填]" if field.get("required") else ""
            unique = " [唯一]" if field.get("unique") else ""
            enum_info = f" ({'/'.join(field['enum_values'])})" if field.get("enum_values") else ""
            print(f"  │    {field['name']}: {field['type']}{enum_info}{req}{unique}")
        if entity.get("constraints"):
            for c in entity["constraints"]:
                print(f"  │    ↳ 约束: {c['type']} on {c['fields']}")
        print(f"  └───────────────────────────────────────")
    print()


def ask_confirm() -> bool:
    """Ask user to confirm before generating."""
    confirm = input("  ✅ 确认以上内容正确？ (yes/no，回车=yes）: ").strip().lower()
    return confirm in ("", "yes", "y", "是")


# ---------------------------------------------------------------------------
# Main plan command
# ---------------------------------------------------------------------------

def run_plan(output_path: Optional[str] = None) -> int:
    """Run the interactive planning session.

    Args:
        output_path: Optional path to save entities.yaml

    Returns:
        Exit code (0 = saved, 1 = aborted, 2 = no entities)
    """
    try:
        # Step 1: Basic info
        name = ask_system_name()
        description = ask_description()
        author = ask_author()

        # Step 2: Entities
        entities = []
        while True:
            entity_names = ask_entity_list()
            for ename in entity_names:
                fields = ask_fields_for_entity(ename)
                constraints = ask_constraints_for_entity(ename, fields)
                entities.append({
                    "name": ename,
                    "description": "",
                    "business_meaning": "",
                    "fields": fields,
                    "constraints": constraints,
                })

            if not ask_more_entities():
                break

        if not entities:
            print("\n  ⚠️  未添加任何实体，退出。")
            return 2

        # Step 3: Summary + confirm
        print_summary(name, entities)
        if not ask_confirm():
            print("\n  ❌ 已取消。")
            return 1

        # Step 4: Build YAML
        yaml_content = build_yaml(name, description, author, entities)

        # Step 5: Save or print
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml_content, encoding="utf-8")
            print(f"\n  ✅ 已保存到: {path}")
            print(f"\n  下一步: python -m cli.main generate --config {path}")
        else:
            print("\n" + "=" * 60)
            print("  📄 entities.yaml 内容")
            print("=" * 60)
            print(yaml_content)
            print()
            print("  💡 复制以上内容保存为 entities.yaml，然后运行:")
            print("     python -m cli.main generate --config entities.yaml")

        return 0

    except KeyboardInterrupt:
        print("\n\n  ❌ 已取消。")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Interactive requirements planner")
    parser.add_argument(
        "--output", "-o",
        help="Output path for entities.yaml",
    )
    args = parser.parse_args()
    sys.exit(run_plan(args.output))
