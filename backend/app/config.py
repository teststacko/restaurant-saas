import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
class ConfigError(RuntimeError): pass

def load_dotenv(path=ROOT / ".env"):
    if not path.exists(): return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"'))

def _need(name):
    load_dotenv(); v = os.environ.get(name)
    if not v: raise ConfigError(f"Missing {name}. Run scripts\\init-env.ps1 (see .env.example).")
    return v
def database_url(): return _need("DATABASE_URL")
def migration_url(): return _need("MIGRATION_DATABASE_URL")

@dataclass(frozen=True)
class Settings:
    env: str; secret_key: str; cookie_secure: bool

def settings() -> Settings:
    key = _need("APP_SECRET_KEY"); env = os.environ.get("APP_ENV", "development")
    if env not in ("development", "test", "production"): raise ConfigError("APP_ENV must be development, test or production")
    if len(key) < 32 or key.lower().startswith("change"): raise ConfigError("APP_SECRET_KEY must be a random value of 32+ characters")
    secure = os.environ.get("COOKIE_SECURE", "").lower() == "true"
    if env == "production" and not secure: raise ConfigError("COOKIE_SECURE must be true in production")
    return Settings(env, key, secure)
