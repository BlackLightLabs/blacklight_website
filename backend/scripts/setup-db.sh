#!/bin/bash
set -e

# Database setup script for Agent Builder
# This script helps with initial database setup and migrations

echo "🔧 Agent Builder - Database Setup"
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start PostgreSQL container
echo "📦 Starting PostgreSQL container..."
docker compose up -d postgres

# Wait for PostgreSQL to be healthy
echo "⏳ Waiting for PostgreSQL to be ready..."
timeout=30
counter=0
until docker compose exec -T postgres pg_isready -U agent_builder -d agent_builder > /dev/null 2>&1; do
    counter=$((counter + 1))
    if [ $counter -gt $timeout ]; then
        echo "❌ Error: PostgreSQL failed to start within ${timeout} seconds"
        exit 1
    fi
    echo "   Waiting... ($counter/$timeout)"
    sleep 1
done

echo "✅ PostgreSQL is ready!"
echo ""

# Run migrations
echo "🔄 Running database migrations..."
uv run alembic upgrade head

echo ""
echo "✅ Database setup complete!"
echo ""
echo "Connection details:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: agent_builder"
echo "  User: agent_builder"
echo "  Password: agent_builder_dev"
echo ""
echo "DATABASE_URL: postgresql://agent_builder:agent_builder_dev@localhost:5432/agent_builder"
