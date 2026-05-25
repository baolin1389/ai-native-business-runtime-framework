"""Main runtime generator module for creating runtime configurations and scaffolding."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GeneratorConfig:
    """Configuration for runtime generation."""

    name: str = "my-runtime"
    output_dir: Path = Path("./generated")
    template_dir: Path | None = None
    include_examples: bool = True
    enable_monitoring: bool = True
    enable_validation: bool = True
    runtime_version: str = "0.1.0"
    extra: dict[str, Any] = field(default_factory=dict)


class RuntimeGenerator:
    """Generator for AI Business Runtime configurations and scaffolding."""

    def __init__(self, config: GeneratorConfig | None = None) -> None:
        """Initialize the runtime generator.

        Args:
            config: Generator configuration. Uses defaults if not provided.
        """
        self.config = config or GeneratorConfig()

    def generate(self) -> dict[str, Any]:
        """Generate runtime configuration.

        Returns:
            Dictionary containing generated configuration files and content.
        """
        output = {
            "runtime_config": self._generate_runtime_config(),
            "agent_configs": self._generate_agent_configs(),
            "pipeline_configs": self._generate_pipeline_configs(),
        }

        if self.config.include_examples:
            output["examples"] = self._generate_examples()

        if self.config.enable_monitoring:
            output["monitoring_config"] = self._generate_monitoring_config()

        if self.config.enable_validation:
            output["validation_config"] = self._generate_validation_config()

        return output

    def _generate_runtime_config(self) -> dict[str, Any]:
        """Generate main runtime configuration."""
        return {
            "version": self.config.runtime_version,
            "name": self.config.name,
            "runtime": {
                "type": "standard",
                "max_agents": 10,
                "default_timeout": 300,
                "event_bus": {
                    "type": "mqtt",
                    "broker": "localhost",
                    "port": 1883,
                },
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "output": "stdout",
            },
        }

    def _generate_agent_configs(self) -> list[dict[str, Any]]:
        """Generate default agent configurations."""
        return [
            {
                "name": "default-agent",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2048,
                "system_prompt": "You are a helpful AI assistant.",
            }
        ]

    def _generate_pipeline_configs(self) -> list[dict[str, Any]]:
        """Generate default pipeline configurations."""
        return [
            {
                "name": "default-pipeline",
                "stages": [
                    {"name": "input", "type": "transform"},
                    {"name": "process", "type": "agent"},
                    {"name": "output", "type": "validate"},
                ],
            }
        ]

    def _generate_examples(self) -> dict[str, str]:
        """Generate example code snippets."""
        return {
            "basic_usage": '''from ai_business_runtime import Runtime, Agent

runtime = Runtime()
agent = Agent(name="assistant", model="gpt-4")
runtime.register(agent)
result = runtime.execute("Hello, world!")
print(result)
''',
            "with_pipeline": '''from ai_business_runtime import Runtime, Pipeline

runtime = Runtime()
pipeline = Pipeline(name="my-pipeline")
runtime.add_pipeline(pipeline)
runtime.run()
''',
        }

    def _generate_monitoring_config(self) -> dict[str, Any]:
        """Generate monitoring configuration."""
        return {
            "enabled": True,
            "metrics_port": 9090,
            "health_check_port": 8080,
            "exporters": ["prometheus", "statsd"],
        }

    def _generate_validation_config(self) -> dict[str, Any]:
        """Generate validation configuration."""
        return {
            "enabled": True,
            "strict_mode": False,
            "validate_agents": True,
            "validate_pipelines": True,
            "validate_inputs": True,
        }

    def save(self, output_path: Path | None = None) -> Path:
        """Save generated configuration to file.

        Args:
            output_path: Path to save configuration. Defaults to output_dir.

        Returns:
            Path to the saved configuration file.
        """
        import json

        output_path = output_path or self.config.output_dir / "runtime_config.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        config = self.generate()
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)

        return output_path
