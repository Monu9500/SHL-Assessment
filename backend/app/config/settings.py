from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_timeout_seconds: float = 28.0
    groq_fallback_models: str = (
        "llama3-8b-8192,llama-3.1-8b-instant,llama-3.1-70b-versatile"
    )

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    catalog_url: str = (
        "https://tcp-us-prod-rnd.shl.com/"
        "voiceRater/shl-ai-hiring/shl_product_catalog.json"
    )

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    top_k_retrieval: int = 48
    backend_data_dir: str = ""

    max_recommendations: int = 10
    evaluator_max_turns: int = 8

    def cors_origins_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    def groq_fallback_model_list(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for raw in self.groq_fallback_models.split(","):
            m = raw.strip()
            if m and m not in seen:
                seen.add(m)
                out.append(m)
        # Ensure configured primary appears first preference
        if self.groq_model and self.groq_model not in out:
            out.insert(0, self.groq_model)
        elif self.groq_model in out:
            out.remove(self.groq_model)
            out.insert(0, self.groq_model)
        return out


@lru_cache
def get_settings() -> Settings:
    return Settings()
