# YALI AI OS - Security Configuration
# This file defines security rules and best practices for the project

[security]
# Never commit these types of files
forbidden_files = [
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    ".env*",
    "secrets.*",
    "config/secrets.*",
    "*/passwords/*",
    "*/credentials/*"
]

# Never commit these patterns (case insensitive)
forbidden_patterns = [
    "password",
    "secret",
    "key",
    "token",
    "auth",
    "credential",
    "private",
    "api_key",
    "access_token",
    "refresh_token",
    "client_secret",
    "client_id",
    "aws_access_key",
    "aws_secret_key",
    "google_api_key",
    "openai_api_key",
    "database_url",
    "db_password",
    "redis_url",
    "mongo_url",
    "email",
    "phone",
    "address",
    "ssn",
    "credit_card",
    "bank"
]

# Allowed environment variables for secrets
allowed_env_vars = [
    "OLLAMA_URL",
    "HUD_HOST",
    "HUD_PORT",
    "WAKE_WORD"
]

[best_practices]
# Use environment variables for all secrets
# Never hardcode API keys, passwords, or tokens
# Use .env files locally (but never commit them)
# Use secrets management services in production
# Regularly audit committed files for sensitive data
# Use the pre-commit hook to prevent accidents

[emergency_procedures]
# If sensitive data is accidentally committed:
# 1. Immediately change all affected credentials
# 2. Remove the sensitive data from git history
# 3. Force push the cleaned history (if necessary)
# 4. Notify affected parties
# 5. Review and improve security procedures