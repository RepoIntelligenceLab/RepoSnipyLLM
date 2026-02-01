-- Global PostgreSQL extensions
-- This script initializes commonly used extensions for a global PostgreSQL instance.
-- NOTE:
-- 1. Extensions are enabled PER DATABASE.
-- 2. You must enable required extensions again in each project database (e.g. reposnipyllm).

-- Vector similarity search support
CREATE EXTENSION IF NOT EXISTS vector;

-- Cryptographic functions (UUIDs, hashes, random bytes)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- UUID generation helpers (uuid_generate_v4, etc.)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
