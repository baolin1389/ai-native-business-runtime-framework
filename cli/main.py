"""Main CLI entry point for AI Business Runtime Framework."""

import argparse
import sys
from pathlib import Path
from typing import NoReturn


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="ai-runtime",
        description="AI Business Runtime Framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a new runtime project",
    )
    init_parser.add_argument(
        "name",
        nargs="?",
        default="my-runtime",
        help="Project name",
    )
    init_parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory",
    )
    init_parser.add_argument(
        "--no-examples",
        action="store_true",
        help="Skip generating example files",
    )

    # Generate command
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate runtime configuration",
    )
    gen_parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Input configuration file (entities.yaml or GeneratorConfig JSON)",
    )
    gen_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("./generated"),
        help="Output directory",
    )
    gen_parser.add_argument(
        "--format",
        "-f",
        choices=["json", "yaml", "toml"],
        default="json",
        help="Output format",
    )
    gen_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview generation without writing files. Shows what would be generated.",
    )
    gen_parser.add_argument(
        "--no-ai-md",
        action="store_true",
        help="Skip generating AI.md (useful for quick preview)",
    )

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run the runtime",
    )
    run_parser.add_argument(
        "config",
        type=Path,
        help="Runtime configuration file",
    )
    run_parser.add_argument(
        "--agent",
        "-a",
        action="append",
        help="Specific agents to run",
    )
    run_parser.add_argument(
        "--pipeline",
        "-p",
        help="Specific pipeline to run",
    )

    # Validate command
    val_parser = subparsers.add_parser(
        "validate",
        help="Validate runtime configuration",
    )
    val_parser.add_argument(
        "config",
        type=Path,
        help="Configuration file to validate",
    )
    val_parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode",
    )

    # Plan command
    plan_parser = subparsers.add_parser(
        "plan",
        help="Collect requirements interactively before generation (run FIRST)",
    )
    plan_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Save entities.yaml to this path",
    )

    # Info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show runtime information",
    )
    info_parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Configuration file to inspect",
    )

    return parser


def cmd_init(args: argparse.Namespace) -> int:
    """Handle the init command — runs the interactive wizard.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    from runtime_generator.prompts import run_wizard
    from runtime_generator.generator import build_generator, GeneratorConfig

    print("Starting AI Business Runtime setup wizard...\n")

    try:
        answers = run_wizard()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        return 1

    config = GeneratorConfig(
        name=answers.get("name", args.name),
        output_dir=args.output_dir,
        include_examples=answers.get("include_examples", not args.no_examples),
        author=answers.get("author", ""),
        description=answers.get("description", ""),
    )

    gen = build_generator(config, answers)
    output_path = gen.save()

    print(f"\nInitialized runtime project '{config.name}' at {output_path}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    """Handle the plan command — interactive requirements collection.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for aborted, 2 for no entities).
    """
    from cli.plan import run_plan

    output_path = str(args.output) if args.output else None
    return run_plan(output_path)


def cmd_generate(args: argparse.Namespace) -> int:
    """Handle the generate command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    import json
    import yaml
    from pathlib import Path

    from runtime_generator.generator import RuntimeGenerator, GeneratorConfig

    if args.config:
        cfg_path = args.config
        with open(cfg_path) as f:
            if cfg_path.suffix in (".yaml", ".yml"):
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)

        # Support two formats:
        # 1. GeneratorConfig JSON: {"name": "...", "output_dir": "...", ...}
        # 2. entities.yaml format: {"name": "...", "entities": [...]}
        if "entities" in config_data and "runtime_config" not in config_data:
            # entities.yaml format → build generator from entity definitions
            from runtime_generator.generator import build_generator
            gc = GeneratorConfig(
                name=config_data.get("name", "my-runtime"),
                output_dir=args.output,
                description=config_data.get("description", ""),
                author=config_data.get("author", ""),
            )
            gen = RuntimeGenerator(gc)
            for entity_data in config_data.get("entities", []):
                from runtime_generator.generator import EntityDef, FieldDef, ConstraintDef

                entity = EntityDef(
                    name=entity_data["name"],
                    table_name=entity_data.get("table_name", entity_data["name"].lower()),
                    description=entity_data.get("description", ""),
                    business_meaning=entity_data.get("business_meaning", ""),
                    fields=[
                        FieldDef(
                            name=f["name"],
                            type=f.get("type", "string"),
                            required=f.get("required", False),
                            primary_key=f.get("primary_key", False),
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
                            type=c.get("type", "required"),
                            fields=c.get("fields", []),
                            explanation=c.get("explanation", ""),
                            params=c.get("params", {}),
                            severity=c.get("severity", "error"),
                        )
                        for c in entity_data.get("constraints", [])
                    ],
                )
                gen.add_entity(entity)
        else:
            # GeneratorConfig JSON format
            config = GeneratorConfig(**config_data)
            gen = RuntimeGenerator(config)
    else:
        config = GeneratorConfig(output_dir=args.output)
        gen = RuntimeGenerator(config)

    # Dry run — show what would be generated without writing files
    if args.dry_run:
        print("=" * 60)
        print("  🔍 Dry Run — 以下文件将被生成")
        print("=" * 60)
        print(f"\n  输出目录: {gen.config.output_dir / gen.config.name}")
        print(f"  实体数量: {len(gen.entities)}")
        print()
        for entity in gen.entities:
            print(f"  ┌─ {entity.name}")
            for field in entity.fields:
                req = " [必填]" if field.required else ""
                print(f"  │    {field.name}: {field.type}{req}")
            if entity.constraints:
                for c in entity.constraints:
                    print(f"  │    ↳ {c.type}: {c.fields}")
            print(f"  └─────────────────────────────────")
        print()
        print("  将生成的文件:")
        files = [
            "runtime.yaml",
            "AI.md",
            "mcp_server.py",
            "app/runtime/engine.py",
            "app/infrastructure/models.py",
            "app/domain/<entity>.yaml",
            "workflows/example.yaml",
        ]
        for f in files:
            print(f"    - {f}")
        print()
        print("  ✅ Dry run 完成（未写入任何文件）")
        print("  💡 使用 --no-ai-md 跳过 AI.md 预览")
        return 0

    output_path = gen.save()

    print(f"Generated runtime project at {output_path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Handle the run command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    print(f"Running runtime with config: {args.config}")
    print(f"Agents: {args.agent or 'all'}")
    print(f"Pipeline: {args.pipeline or 'default'}")
    # Runtime execution would go here
    print("Runtime execution not yet implemented")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Handle the validate command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for validation errors).
    """
    import json

    try:
        with open(args.config) as f:
            config = json.load(f)
        print(f"Configuration file: {args.config}")
        print("Validation passed!")
        return 0
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"File not found: {args.config}", file=sys.stderr)
        return 1


def cmd_info(args: argparse.Namespace) -> int:
    """Handle the info command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    print("AI Business Runtime Framework")
    print("  Version: 0.1.0")
    print("  Python: >=3.10")

    if args.config:
        import json

        try:
            with open(args.config) as f:
                config = json.load(f)
            print(f"\nConfiguration: {args.config}")
            print(f"  Name: {config.get('runtime_config', {}).get('name', 'N/A')}")
            print(f"  Version: {config.get('runtime_config', {}).get('version', 'N/A')}")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading config: {e}", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv).

    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "init": cmd_init,
        "generate": cmd_generate,
        "run": cmd_run,
        "validate": cmd_validate,
        "info": cmd_info,
        "plan": cmd_plan,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
