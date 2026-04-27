"""Configuration management with Pydantic."""

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from platformdirs import user_config_dir
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseModel):
    """Configuration for a specific LLM provider."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None


class SerpentConfig(BaseSettings):
    """Main configuration for Serpent."""
    model_config = SettingsConfigDict(
        env_prefix="SERPENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = Field(default="anthropic", description="Default LLM provider")
    model: str = Field(default="claude-sonnet-4-20250514", description="Default model")
    api_key: Optional[str] = Field(default=None, description="API key for default provider")
    working_dir: Path = Field(default=Path("."), description="Working directory")
    
    # Tool settings
    auto_confirm_reads: bool = Field(default=True, description="Auto-confirm file reads")
    auto_confirm_writes: bool = Field(default=False, description="Auto-confirm file writes")
    auto_confirm_bash: bool = Field(default=False, description="Always ask for bash commands")
    max_file_size_mb: float = Field(default=1.0, description="Max file size in MB")
    
    # UI settings
    show_thinking: bool = Field(default=True, description="Show model thinking process")
    context_warning_threshold: float = Field(default=0.8, description="Context window warning threshold")
    
    # Session settings
    session_dir: Path = Field(default_factory=lambda: Path(user_config_dir("serpent")) / "sessions")
    
    # Provider-specific configs
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)

    @field_validator("working_dir", "session_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: str | Path) -> Path:
        if isinstance(v, str):
            v = Path(v)
        return v.expanduser().resolve()


def _substitute_env_vars(data: dict) -> dict:
    """Substitute ${VAR} and $VAR in config values."""
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            def replacer(match: re.Match) -> str:
                var_name = match.group(1) or match.group(2)
                return os.environ.get(var_name, "")
            value = re.sub(r"\$\{(\w+)\}|\$(\w+)", replacer, value)
            result[key] = value
        elif isinstance(value, dict):
            result[key] = _substitute_env_vars(value)
        else:
            result[key] = value
    return result


def load_config() -> SerpentConfig:
    """Load configuration from files and environment."""
    config = SerpentConfig()
    
    config_paths = [
        Path("serpent.yaml"),
        Path(".serpent.yaml"),
        Path(user_config_dir("serpent")) / "config.yaml",
        Path.home() / ".config" / "serpent" / "config.yaml",
    ]
    
    for path in config_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                
                data = _substitute_env_vars(data)
                
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            except Exception:
                continue
    
    config.session_dir.mkdir(parents=True, exist_ok=True)
    
    return config