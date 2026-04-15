"""
Application settings configuration.

Uses Pydantic BaseSettings to load and validate environment variables.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the path to the backend directory (where .env is located)
BACKEND_DIR = Path(__file__).parent.parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    grok_api_key: str = ""

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS Configuration
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Database Configuration
    # Option 1: Provide full DATABASE_URL directly
    database_url: Optional[str] = None

    # Option 2: Provide individual components (will construct DATABASE_URL)
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_name: Optional[str] = None

    # Database connection pool settings
    database_pool_size: int = 10  # Connection pool size
    database_max_overflow: int = 20  # Max connections beyond pool_size
    database_pool_pre_ping: bool = True  # Verify connections before using them
    database_echo: bool = False  # Set to True for SQL query logging

    # Authentication Configuration
    jwt_secret: str = ""  # Required in production, can be empty in development
    jwt_lifetime_seconds: int = 1800  # 30 minutes default

    # Environment Configuration
    environment: str = "development"  # development, staging, production

    # Logging Configuration
    log_level: str = "INFO"  # Global default log level
    log_level_auth: Optional[str] = None  # Auth feature log level (defaults to log_level)
    log_level_agents: Optional[str] = None  # Agents feature log level
    log_level_executions: Optional[str] = None  # Executions feature log level
    log_format: str = "console"  # "console" or "json"
    log_file_enabled: bool = True  # Enable file logging
    log_file_path: str = "logs/blacklight.log"  # Log file path
    log_rotation: str = "daily"  # "daily" or "size"
    log_retention_days: int = 30  # Days to retain logs
    log_max_size_mb: int = 100  # Max log file size in MB (for size rotation)
    slow_query_threshold_ms: int = 1000  # Log queries slower than this (in milliseconds)
    log_sampling_rate: float = 0.1  # Sample rate for high-traffic endpoints (0.0-1.0)

    # Error Handling Configuration
    expose_error_details: bool = False  # Expose detailed error info (set True for development)
    retry_max_attempts: int = 3  # Maximum retry attempts for transient failures
    circuit_breaker_threshold: int = 5  # Failures before opening circuit breaker

    # OpenTelemetry Configuration
    otel_enabled: bool = True  # Enable OpenTelemetry metrics and tracing
    otel_service_name: str = "blacklight"  # Service name for telemetry
    otel_service_version: str = "0.1.0"  # Service version
    otel_environment: str = ""  # Deployment environment (will default to self.environment)

    # OpenTelemetry Exporters
    otel_metrics_exporter: str = "console"  # "console", "otlp", "prometheus", or "none"
    otel_traces_exporter: str = "console"  # "console", "otlp", "jaeger", or "none"

    # OTLP Exporter Configuration (for backend observability platforms like Jaeger, Tempo, etc.)
    otel_otlp_endpoint: str = "http://localhost:4317"  # OTLP gRPC endpoint
    otel_otlp_insecure: bool = True  # Use insecure connection (HTTP) for local development
    otel_otlp_headers: str = ""  # Additional headers (e.g., "api-key=xxx")

    # Prometheus Exporter Configuration (for /metrics endpoint)
    otel_prometheus_port: int = 9090  # Port for Prometheus scraping endpoint

    # Sampling Configuration
    otel_traces_sampler: str = "always_on"  # "always_on", "always_off", "traceidratio", "parentbased_always_on"
    otel_traces_sampler_arg: float = 1.0  # Sampling rate for traceidratio sampler (0.0-1.0)

    # OAuth2 Configuration
    oauth2_enabled: bool = False  # Master toggle for OAuth2 feature
    backend_url: str = "http://localhost:8000"  # Backend API public URL (for OAuth redirect_uri)
    frontend_url: str = "http://localhost:5173"  # Frontend URL for OAuth callbacks

    # Google OAuth2
    google_oauth_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""

    # Microsoft OAuth2
    microsoft_oauth_enabled: bool = False
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant: str = "common"

    # GitHub OAuth2
    github_oauth_enabled: bool = False
    github_client_id: str = ""
    github_client_secret: str = ""

    # Generic OIDC Provider
    oidc_enabled: bool = False
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_well_known_url: str = ""
    oidc_provider_name: str = "CustomOIDC"

    @model_validator(mode='after')
    def validate_oauth_credentials(self):
        """
        Validate OAuth2 credentials when providers are enabled.

        Ensures that when OAuth2 is enabled and a provider is enabled,
        the required credentials (client_id and client_secret) are provided.
        """
        if not self.oauth2_enabled:
            # OAuth2 disabled globally, no validation needed
            return self

        # Validate Google OAuth
        if self.google_oauth_enabled:
            if not self.google_client_id:
                raise ValueError(
                    "GOOGLE_CLIENT_ID is required when GOOGLE_OAUTH_ENABLED=true"
                )
            if not self.google_client_secret:
                raise ValueError(
                    "GOOGLE_CLIENT_SECRET is required when GOOGLE_OAUTH_ENABLED=true"
                )

        # Validate Microsoft OAuth
        if self.microsoft_oauth_enabled:
            if not self.microsoft_client_id:
                raise ValueError(
                    "MICROSOFT_CLIENT_ID is required when MICROSOFT_OAUTH_ENABLED=true"
                )
            if not self.microsoft_client_secret:
                raise ValueError(
                    "MICROSOFT_CLIENT_SECRET is required when MICROSOFT_OAUTH_ENABLED=true"
                )

        # Validate GitHub OAuth
        if self.github_oauth_enabled:
            if not self.github_client_id:
                raise ValueError(
                    "GITHUB_CLIENT_ID is required when GITHUB_OAUTH_ENABLED=true"
                )
            if not self.github_client_secret:
                raise ValueError(
                    "GITHUB_CLIENT_SECRET is required when GITHUB_OAUTH_ENABLED=true"
                )

        # Validate OIDC Provider
        if self.oidc_enabled:
            if not self.oidc_client_id:
                raise ValueError(
                    "OIDC_CLIENT_ID is required when OIDC_ENABLED=true"
                )
            if not self.oidc_client_secret:
                raise ValueError(
                    "OIDC_CLIENT_SECRET is required when OIDC_ENABLED=true"
                )
            if not self.oidc_well_known_url:
                raise ValueError(
                    "OIDC_WELL_KNOWN_URL is required when OIDC_ENABLED=true"
                )

        # Ensure at least one provider is enabled if OAuth2 is enabled
        providers_enabled = any([
            self.google_oauth_enabled,
            self.microsoft_oauth_enabled,
            self.github_oauth_enabled,
            self.oidc_enabled,
        ])
        if not providers_enabled:
            raise ValueError(
                "OAUTH2_ENABLED=true but no OAuth providers are enabled. "
                "Enable at least one provider: GOOGLE_OAUTH_ENABLED, "
                "MICROSOFT_OAUTH_ENABLED, GITHUB_OAUTH_ENABLED, or OIDC_ENABLED"
            )

        return self

    @model_validator(mode='after')
    def configure_environment_defaults(self):
        """
        Apply environment-specific defaults.

        - In development: expose_error_details defaults to True
        - In production: expose_error_details defaults to False (security)
        - Set otel_environment to environment if not provided
        """
        # Auto-enable detailed errors in development if not explicitly set
        if self.is_development and self.expose_error_details is False:
            # Check if it was explicitly set to False via env var
            import os
            if 'EXPOSE_ERROR_DETAILS' not in os.environ:
                self.expose_error_details = True

        # Set OpenTelemetry environment from main environment if not provided
        if not self.otel_environment:
            self.otel_environment = self.environment

        return self

    @model_validator(mode='after')
    def construct_database_url(self):
        """
        Construct database_url from individual components if not provided directly.

        Priority:
        1. If DATABASE_URL is provided, use it as-is
        2. If individual components (DB_HOST, DB_USER, etc.) are provided, construct URL
        3. Raise error if neither is provided
        """
        if self.database_url:
            # DATABASE_URL provided directly, use it
            return self

        # Try to construct from components
        if all([self.db_host, self.db_user, self.db_password, self.db_name]):
            # All required components provided
            port = self.db_port or 5432  # Default PostgreSQL port
            self.database_url = (
                f"postgresql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{port}/{self.db_name}"
            )
            return self

        # Neither full URL nor complete components provided
        raise ValueError(
            "Database configuration incomplete. Provide either:\n"
            "  1. DATABASE_URL (full connection string), OR\n"
            "  2. All of: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME (and optionally DB_PORT)"
        )

    @field_validator('database_url', mode='after')
    @classmethod
    def validate_database_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate database URL if provided."""
        if v and not v.startswith(('postgresql://', 'postgres://')):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql://' or 'postgres://'"
            )
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def effective_log_level_auth(self) -> str:
        """Get effective log level for auth feature."""
        return self.log_level_auth or self.log_level

    @property
    def effective_log_level_agents(self) -> str:
        """Get effective log level for agents feature."""
        return self.log_level_agents or self.log_level

    @property
    def effective_log_level_executions(self) -> str:
        """Get effective log level for executions feature."""
        return self.log_level_executions or self.log_level


# Global settings instance
settings = Settings()
