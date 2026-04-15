"""
Blacklight - AI Agent Builder Platform

A conversational AI platform that enables users to create custom LangGraph agents
through natural language interactions. Users describe what they want, and the AI
assistant asks clarifying questions to generate fully functional agents without
requiring users to write code.

Project Structure:
    - common/: Shared infrastructure (database, LLM config, base classes)
    - features/: Feature modules organized by business domain
        - agents/: Agent creation and build system
        - auth/: Authentication and authorization (RBAC)
        - executions/: Agent execution tracking
    - middleware/: Request processing middleware
    - dependencies/: FastAPI dependency injection providers

Key Technologies:
    - FastAPI: Web framework
    - SQLAlchemy 2.0: ORM with async support
    - LangChain/LangGraph: LLM orchestration and agent workflows
    - PostgreSQL: Database
    - FastAPI-Users: Authentication

Architecture:
    This project uses a feature-based architecture (modular monolith pattern).
    Code is organized by business domain rather than technical layer, making it
    easier to understand, test, and potentially extract into microservices.

For detailed documentation, see CLAUDE.md in the project root.
"""

__version__ = "0.1.0"


def main() -> None:
    """Entry point for CLI (if needed in future)."""
    print("Blacklight Agent Builder Platform v" + __version__)
