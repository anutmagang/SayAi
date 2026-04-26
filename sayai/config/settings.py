from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _defaults_path() -> Path:
    return Path(__file__).resolve().parent / "defaults.yaml"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


class LLMSettings(BaseModel):
    default_model: str = "anthropic/claude-3-5-haiku-20241022"  # LiteLLM model id
    routing: dict[str, str] = Field(default_factory=dict)
    fallback_chains: dict[str, list[str]] = Field(default_factory=dict)


class AgentSettings(BaseModel):
    max_parallel: int = 4
    max_iterations: int = 10
    load_approved_skills: bool = True
    approved_skills_max_count: int = 12
    approved_skills_max_chars: int = 12000
    approved_skills_per_skill_chars: int = 4000


class ToolSettings(BaseModel):
    bash_timeout: int = 30
    bash_max_output: int = 5000
    allowed_dirs: list[str] = Field(default_factory=list)


class MemorySettings(BaseModel):
    short_term_tokens: int = 8000
    qdrant_enabled: bool = False
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "sayai_memory"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    index_on_read: bool = True
    index_on_write: bool = True
    index_max_chunk_chars: int = 4000
    redis_url: str = ""


class MCPSettings(BaseModel):
    """HTTP-style MCP servers (blueprint); stdio MCP can be added later."""

    servers: list[dict[str, str]] = Field(default_factory=list)


class ToolExtraSettings(BaseModel):
    test_command: str = "pytest -q"
    eslint_path: str = "eslint"
    pyright_command: str = "basedpyright"


class OrchestratorSettings(BaseModel):
    use_dag: bool = True


class ServerSettings(BaseModel):
    """Minimal HTTP listener for /health (VPS / load balancer probes)."""

    host: str = "127.0.0.1"
    port: int = 8765


class FeatureSettings(BaseModel):
    reflect_after_dag: bool = False
    cost_log_path: str = ""


class SkillHunterSettings(BaseModel):
    enabled: bool = False
    min_score: float = 0.6
    max_proposals_per_run: int = 12
    github_query: str = "mcp server in:name,description,readme"
    pypi_query: str = "mcp agent tool"
    mcp_registry_url: str = ""
    # ClawHub (Convex public API used by clawhub.ai)
    clawhub_enabled: bool = False
    clawhub_convex_url: str = "https://wry-manatee-359.convex.cloud"
    clawhub_sort: str = "downloads"
    clawhub_num_per_page: int = 25
    clawhub_max_pages: int = 2
    clawhub_fetch_readme: bool = True
    clawhub_delay_sec: float = 0.35
    clawhub_non_suspicious_only: bool = False
    # Awesome-style Markdown lists (raw GitHub README URLs)
    awesome_enabled: bool = False
    awesome_raw_readme_urls: list[str] = Field(default_factory=list)
    awesome_max_repos: int = 40
    autoskills_map_enabled: bool = False
    autoskills_map_url: str = ""
    autoskills_map_max_items: int = 80
    stack_detection_enabled: bool = True


class AdminSettings(BaseModel):
    require_approval: bool = True
    notify_tui: bool = True
    notify: list[dict[str, Any]] = Field(default_factory=list)


class SayAiSettings(BaseModel):
    version: str = "0.1.0"
    mode: str = "local"
    log_level: str = "INFO"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SAYAI_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    sayai: SayAiSettings = Field(default_factory=SayAiSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    agents: AgentSettings = Field(default_factory=AgentSettings)
    tools: ToolSettings = Field(default_factory=ToolSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    orchestrator: OrchestratorSettings = Field(default_factory=OrchestratorSettings)
    skillhunter: SkillHunterSettings = Field(default_factory=SkillHunterSettings)
    admin: AdminSettings = Field(default_factory=AdminSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    tool_extra: ToolExtraSettings = Field(default_factory=ToolExtraSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    features: FeatureSettings = Field(default_factory=FeatureSettings)

    data_dir: Path = Field(default_factory=lambda: Path.home() / ".local" / "share" / "sayai")

    @classmethod
    def from_merged_yaml(cls, user_path: Path | None = None) -> AppSettings:
        base = _load_yaml(_defaults_path())
        if user_path and user_path.is_file():
            base = _deep_merge(base, _load_yaml(user_path))
        return cls.model_validate(base)


def config_paths() -> tuple[Path, Path]:
    root = Path(os.environ.get("SAYAI_CONFIG_DIR", Path.home() / ".config" / "sayai"))
    return root / "settings.yaml", root / ".env"


@lru_cache
def load_config() -> AppSettings:
    settings_file, env_file = config_paths()
    if env_file.is_file():
        from dotenv import load_dotenv

        load_dotenv(env_file)
    return AppSettings.from_merged_yaml(settings_file if settings_file.is_file() else None)
