from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ProviderName = Literal["heuristic", "openai", "openai_compatible", "anthropic"]


class HostedProviderSettings(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    simple_model: str | None = None
    complex_model: str | None = None
    timeout_seconds: int | None = None


class GuiRuntimeProviders(BaseModel):
    openai: HostedProviderSettings = Field(default_factory=HostedProviderSettings)
    openai_compatible: HostedProviderSettings = Field(default_factory=HostedProviderSettings)
    anthropic: HostedProviderSettings = Field(default_factory=HostedProviderSettings)


class GuiRuntimeConfig(BaseModel):
    default_provider: ProviderName = "heuristic"
    providers: GuiRuntimeProviders = Field(default_factory=GuiRuntimeProviders)
