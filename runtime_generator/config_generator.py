"""Configuration file generator for runtime components."""

from pathlib import Path
from typing import Any


class ConfigGenerator:
    """Generate various runtime configuration files."""

    @staticmethod
    def generate_yaml_config(config: dict[str, Any]) -> str:
        """Generate YAML configuration string.

        Args:
            config: Configuration dictionary.

        Returns:
            YAML formatted string.
        """
        import yaml

        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    @staticmethod
    def generate_toml_config(config: dict[str, Any]) -> str:
        """Generate TOML configuration string.

        Args:
            config: Configuration dictionary.

        Returns:
            TOML formatted string.
        """
        import tomli

        return tomli.dumps(config)

    @staticmethod
    def generate_env_file(config: dict[str, Any], prefix: str = "RUNTIME") -> str:
        """Generate .env file from configuration.

        Args:
            config: Configuration dictionary.
            prefix: Environment variable prefix.

        Returns:
            .env formatted string.
        """
        lines = []
        for key, value in config.items():
            env_key = f"{prefix}_{key.upper()}"
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    lines.append(f"{env_key}_{sub_key.upper()}={sub_value}")
            elif isinstance(value, (list, tuple)):
                lines.append(f"{env_key}={','.join(str(v) for v in value)}")
            else:
                lines.append(f"{env_key}={value}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def save_config(
        config: dict[str, Any],
        output_path: Path,
        format: str = "json",
    ) -> Path:
        """Save configuration to file.

        Args:
            config: Configuration dictionary.
            output_path: Path to save the configuration.
            format: Output format (json, yaml, toml).

        Returns:
            Path to the saved file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            import json

            with open(output_path, "w") as f:
                json.dump(config, f, indent=2)
        elif format == "yaml":
            with open(output_path, "w") as f:
                f.write(ConfigGenerator.generate_yaml_config(config))
        elif format == "toml":
            with open(output_path, "w") as f:
                f.write(ConfigGenerator.generate_toml_config(config))
        else:
            raise ValueError(f"Unsupported format: {format}")

        return output_path
