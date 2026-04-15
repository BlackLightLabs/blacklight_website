#!/bin/bash
set -e

# This script runs automatically when the PostgreSQL container starts for the first time
# It's executed by docker-entrypoint-initdb.d

echo "Initializing Agent Builder database..."

# The database is already created by POSTGRES_DB environment variable
# This script is here for any additional initialization needed

echo "Database initialization complete!"
