"""
Feature Modules

This package contains all feature modules organized by business domain.
Each feature is self-contained with its own models, repositories, services,
routes, and tests.

Available Features:
    - agents: Agent creation, build pipeline, and version management
    - auth: User authentication, RBAC, audit logging, and user settings
    - executions: Agent execution tracking and history

Feature Structure:
    Each feature module follows a consistent structure:
        - models.py: SQLAlchemy ORM models
        - repositories.py: Data access layer
        - services.py: Business logic layer
        - routes.py: FastAPI route handlers
        - schemas.py: Pydantic request/response models
        - dependencies.py: Dependency injection providers
        - tests/: Unit, integration, and system tests

Architecture Principles:
    - Use absolute imports (never relative imports)
    - Features communicate through well-defined service interfaces
    - All database operations go through repositories (no direct SQLAlchemy in routes)
    - Business logic lives in services, not route handlers
    - Tests are colocated with the code they test

For more information, see CLAUDE.md in the project root.
"""
