from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ProviderName = Literal["heuristic", "openai", "openai_compatible", "anthropic"]
ProviderPolicyName = Literal["heuristic", "openai", "openai_compatible", "anthropic", "stub"]


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


class ProviderPolicySettings(BaseModel):
    max_concurrent_per_run: int | None = None
    max_concurrent_global: int | None = None
    max_call_attempts: int | None = None
    max_resume_attempts: int | None = None


class GuiRuntimeProviderPolicies(BaseModel):
    openai: ProviderPolicySettings = Field(default_factory=ProviderPolicySettings)
    openai_compatible: ProviderPolicySettings = Field(default_factory=ProviderPolicySettings)
    anthropic: ProviderPolicySettings = Field(default_factory=ProviderPolicySettings)
    heuristic: ProviderPolicySettings = Field(default_factory=ProviderPolicySettings)
    stub: ProviderPolicySettings = Field(default_factory=ProviderPolicySettings)


class GuiRuntimeConfig(BaseModel):
    default_provider: ProviderName = "heuristic"
    providers: GuiRuntimeProviders = Field(default_factory=GuiRuntimeProviders)
    provider_policies: GuiRuntimeProviderPolicies = Field(default_factory=GuiRuntimeProviderPolicies)
