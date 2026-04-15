"""
LLM Provider Configuration

Supports multiple LLM providers with caching.
"""

from enum import Enum

from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.blacklight.common.settings import settings


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    XAI_GROK = "xai_grok"
    LMSTUDIO = "lmstudio"


class LLMConfig:
    """Configuration for LLM providers"""

    # xAI/Grok API endpoint (OpenAI-compatible)
    XAI_BASE_URL = "https://api.x.ai/v1"

    # LMStudio local API endpoint (OpenAI-compatible)
    LMSTUDIO_BASE_URL = "http://localhost:1234/v1"

    # Default models for each provider
    DEFAULT_MODELS = {
        LLMProvider.OPENAI: "gpt-4o-mini",
        LLMProvider.XAI_GROK: "grok-4-fast-non-reasoning",  # Fast model for testing
        LLMProvider.LMSTUDIO: "local-model",  # Model name from LMStudio
    }

    @staticmethod
    def setup_caching():
        """Enable in-memory caching for LLM responses"""
        set_llm_cache(InMemoryCache())

    @staticmethod
    def get_llm(
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        streaming: bool = False,
        callbacks: list | None = None,
    ) -> BaseChatModel:
        """
        Get configured LLM instance based on provider.

        Args:
            provider: LLM provider (openai, xai_grok, or lmstudio). Defaults to env var LLM_PROVIDER or xai_grok.
            model: Model name. Defaults to provider's default model or env var LLM_MODEL.
            temperature: Temperature for generation.
            streaming: Enable streaming responses.
            callbacks: Callback handlers for streaming.

        Returns:
            Configured LLM instance

        Raises:
            ValueError: If provider is not supported or API key is missing
        """
        # Determine provider
        if provider is None:
            provider = settings.llm_provider

        try:
            provider_enum = LLMProvider(provider.lower())
        except ValueError:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: {[p.value for p in LLMProvider]}"
            )

        # Determine model
        if model is None:
            model = settings.llm_model or LLMConfig.DEFAULT_MODELS[provider_enum]

        # Configure based on provider
        if provider_enum == LLMProvider.OPENAI:
            api_key = settings.openai_api_key
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required for OpenAI provider"
                )

            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=SecretStr(api_key) if api_key else None,
                streaming=streaming,
                callbacks=callbacks or [],
            )

        elif provider_enum == LLMProvider.XAI_GROK:
            api_key = settings.grok_api_key
            if not api_key:
                raise ValueError(
                    "GROK_API_KEY environment variable is required for xAI Grok provider"
                )

            # xAI uses OpenAI-compatible API
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=SecretStr(api_key) if api_key else None,
                base_url=LLMConfig.XAI_BASE_URL,
                streaming=streaming,
                callbacks=callbacks or [],
            )

        elif provider_enum == LLMProvider.LMSTUDIO:
            # LMStudio runs locally and doesn't require a real API key
            api_key = "not-needed"

            # LMStudio uses OpenAI-compatible API
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=SecretStr(api_key),
                base_url=LLMConfig.LMSTUDIO_BASE_URL,
                streaming=streaming,
                callbacks=callbacks or [],
            )

        else:
            raise ValueError(f"Provider {provider_enum} not implemented")


# Setup caching on module import
LLMConfig.setup_caching()
