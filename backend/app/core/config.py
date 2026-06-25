from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/jobagent"
    redis_url: str = "redis://localhost:6379"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    serpapi_key: str = ""
    secret_key: str = "change-me-in-production"
    upload_dir: str = "/app/uploads"
    app_url: str = "http://localhost:3000"

    # Email (SendGrid preferred, SMTP fallback)
    sendgrid_api_key: str = ""
    email_from: str = "noreply@jobagent.app"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""

    # LinkedIn OAuth
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8000/api/auth/linkedin/callback"

    # Ollama (local AI — free, runs on your M3 Pro)
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:14b"

    class Config:
        env_file = ".env"


settings = Settings()
