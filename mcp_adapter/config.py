"""
MCP Adapter Configuration

Handles configuration loading and provider setup.
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

import yaml


class TransportType(Enum):
    HTTP = "http"
    WEBSOCKET = "websocket"
    STREAMING = "streaming"


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider"""
    name: str
    api_key_env: str
    endpoint: str
    default_model: str
    capabilities: List[str] = field(default_factory=list)
    timeout_seconds: int = 60
    max_retries: int = 3
    extra_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class TransportSettings:
    """Transport layer settings"""
    type: TransportType = TransportType.HTTP
    pool_size: int = 10
    keep_alive: bool = True
    verify_ssl: bool = True
    proxy_url: Optional[str] = None


@dataclass
class RateLimitSettings:
    """Rate limit configuration"""
    requests_per_minute: int = 60
    tokens_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    tokens_per_day: Optional[int] = None


@dataclass
class MCPAdapterConfig:
    """Main MCP adapter configuration"""
    default_provider: str = "openai"
    timeout_seconds: int = 60
    max_retries: int = 3
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    transport: TransportSettings = field(default_factory=TransportSettings)
    rate_limit: RateLimitSettings = field(default_factory=RateLimitSettings)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPAdapterConfig":
        """Create config from dictionary"""
        providers = {}
        for name, pdata in data.get("providers", {}).items():
            providers[name] = ProviderConfig(
                name=name,
                api_key_env=pdata.get("api_key_env", ""),
                endpoint=pdata.get("endpoint", ""),
                default_model=pdata.get("default_model", ""),
                capabilities=pdata.get("capabilities", []),
                timeout_seconds=pdata.get("timeout_seconds", 60),
                max_retries=pdata.get("max_retries", 3),
                extra_headers=pdata.get("extra_headers", {}),
            )

        transport_data = data.get("transport", {})
        transport = TransportSettings(
            type=TransportType(transport_data.get("type", "http")),
            pool_size=transport_data.get("pool_size", 10),
            keep_alive=transport_data.get("keep_alive", True),
            verify_ssl=transport_data.get("verify_ssl", True),
            proxy_url=transport_data.get("proxy_url"),
        )

        rate_limit_data = data.get("rate_limit", {})
        rate_limit = RateLimitSettings(
            requests_per_minute=rate_limit_data.get("requests_per_minute", 60),
            tokens_per_minute=rate_limit_data.get("tokens_per_minute"),
            requests_per_day=rate_limit_data.get("requests_per_day"),
            tokens_per_day=rate_limit_data.get("tokens_per_day"),
        )

        return cls(
            default_provider=data.get("default_provider", "openai"),
            timeout_seconds=data.get("timeout_seconds", 60),
            max_retries=data.get("max_retries", 3),
            providers=providers,
            transport=transport,
            rate_limit=rate_limit,
        )

    @classmethod
    def from_yaml(cls, path: str) -> "MCPAdapterConfig":
        """Load configuration from YAML file"""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    def get_provider(self, name: Optional[str] = None) -> ProviderConfig:
        """Get provider configuration by name"""
        provider_name = name or self.default_provider
        if provider_name not in self.providers:
            raise ValueError(f"Provider not found: {provider_name}")
        return self.providers[provider_name]

    def get_api_key(self, provider_name: Optional[str] = None) -> str:
        """Get API key from environment for provider"""
        provider = self.get_provider(provider_name)
        api_key = os.environ.get(provider.api_key_env)
        if not api_key:
            raise ValueError(f"API key not set: {provider.api_key_env}")
        return api_key


def load_config(config_path: Optional[str] = None) -> MCPAdapterConfig:
    """
    Load MCP adapter configuration.

    Args:
        config_path: Path to YAML config file. If None, uses default config.

    Returns:
        MCPAdapterConfig instance
    """
    if config_path:
        return MCPAdapterConfig.from_yaml(config_path)

    # Default configuration with common providers
    return MCPAdapterConfig(
        default_provider="openai",
        providers={
            "openai": ProviderConfig(
                name="openai",
                api_key_env="OPENAI_API_KEY",
                endpoint="https://api.openai.com/v1",
                default_model="gpt-4o",
                capabilities=["chat_completions", "embeddings", "function_calling", "vision"],
            ),
            "anthropic": ProviderConfig(
                name="anthropic",
                api_key_env="ANTHROPIC_API_KEY",
                endpoint="https://api.anthropic.com/v1",
                default_model="claude-3-5-sonnet-20241022",
                capabilities=["completions", "tool_use", "vision", "streaming"],
            ),
            "google": ProviderConfig(
                name="google",
                api_key_env="GOOGLE_API_KEY",
                endpoint="https://generativelanguage.googleapis.com/v1",
                default_model="gemini-1.5-pro",
                capabilities=["completions", "function_calling", "batch"],
            ),
        }
    )
