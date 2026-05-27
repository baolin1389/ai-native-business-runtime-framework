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
        help="Input configuration file",
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


def cmd_generate(args: argparse.Namespace) -> int:
    """Handle the generate command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    from runtime_generator import RuntimeGenerator, GeneratorConfig, ConfigGenerator

    if args.config:
        import json

        with open(args.config) as f:
            config_data = json.load(f)
        config = GeneratorConfig(**config_data)
    else:
        config = GeneratorConfig(output_dir=args.output)

    generator = RuntimeGenerator(config)
    generated = generator.generate()

    output_path = ConfigGenerator.save_config(
        generated,
        args.output / f"runtime_config.{args.format}",
        format=args.format,
    )

    print(f"Generated configuration at {output_path}")
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
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
