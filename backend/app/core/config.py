"""Uygulama ayarları — .env üzerinden yüklenir."""
from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "change-me"  # noqa: S105
    app_base_url: str = "http://localhost:8000"

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    # Celery — dev'de False (FastAPI BackgroundTasks ile aynı process), prod'da True
    celery_enabled: bool = False

    # Tek-tenant fallback (legacy MVP) — multi-tenant'ta bu alanlar tenant tablosundan
    # ve Vault'tan okunur. Vault yoksa bu env'ler kullanılır.
    sap_service_layer_url: str = ""
    sap_company_db: str = ""
    sap_username: str = ""
    sap_password: str = ""
    sap_verify_ssl: bool = False
    sap_session_timeout_minutes: int = 30
    sap_max_concurrent_sessions: int = 4
    # Dry-run: SAP'a yazma, sadece JSON payload'ı üret. Tenant'ta override edilebilir.
    sap_dry_run: bool = True

    # Yüksek güven (≥0.95) pipeline sonucunu otomatik SAP'a gönder.
    # Pilot'ta False — operatör her belgeyi kontrol eder. Prod'da True yapılabilir.
    auto_submit_on_high_confidence: bool = False

    # HashiCorp Vault — secret kaynağı (SAP credential, OpenRouter key vs.)
    vault_enabled: bool = False
    vault_addr: str = "http://localhost:8200"
    vault_token: str = ""
    vault_kv_mount: str = "kv"
    vault_secret_cache_ttl_seconds: int = 300

    # Object storage — S3 (prod) / MinIO (dev) / local (fallback)
    storage_backend: str = "local"  # "local" | "minio" | "s3"
    s3_endpoint_url: str = ""  # MinIO için zorunlu, AWS için boş
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "sapb1-agent"
    s3_region: str = "us-east-1"
    s3_signed_url_expire_seconds: int = 3600

    # OpenRouter — OpenAI-uyumlu, tek API üzerinden Claude/GPT/Gemini erişimi
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # OpenRouter model ID formatı: "vendor/model" — https://openrouter.ai/models
    # Güvenli default'lar: garantili mevcut isimler. Yeni model'a geçmek için
    # .env'den override et (örn. LLM_MODEL_DEFAULT=anthropic/claude-sonnet-4.5)
    llm_model_default: str = "anthropic/claude-3.5-sonnet"
    llm_model_hard: str = "anthropic/claude-3-opus"
    llm_model_fast: str = "anthropic/claude-3.5-haiku"
    # OpenRouter analytics (opsiyonel — referer + app adı)
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_app_name: str = "SAP B1 AI Agent"

    email_imap_host: str = ""
    email_imap_port: int = 993
    email_username: str = ""
    email_password: str = ""
    email_folder: str = "INBOX"
    email_poll_interval_seconds: int = 300

    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""

    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Data retention — KVKK uyumu
    data_retention_days_documents: int = 365
    data_retention_days_llm_calls: int = 730
    data_retention_days_audit_log: int = 2555  # 7 yıl

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> Settings:
        if self.app_env == "production":
            if self.app_secret_key == "change-me":  # noqa: S105
                raise ValueError(
                    "Production'da APP_SECRET_KEY varsayılan değer olamaz; "
                    "`openssl rand -hex 32` ile üretin."
                )
            if not self.sap_verify_ssl:
                raise ValueError(
                    "Production'da SAP_VERIFY_SSL=true zorunlu (sertifika doğrulama)."
                )
        return self


settings = Settings()  # type: ignore[call-arg]
