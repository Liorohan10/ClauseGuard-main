from pydantic_settings import BaseSettings

from dotenv import load_dotenv


load_dotenv()


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o"
    elasticsearch_url: str = "http://localhost:9200"
    embedding_model: str = "all-MiniLM-L6-v2"
    es_contracts_index: str = "clauseguard-contracts"
    es_clauses_index: str = "clauseguard-clauses"
    es_cuad_index: str = "clauseguard-cuad"
    openai_dump_dir: str = "openai_dumps"
    tavily_api_key: str = ""

    @property
    def llm_api_key(self) -> str:
        return self.openai_api_key

    @property
    def llm_base_url(self) -> str:
        return self.openai_base_url

    @property
    def llm_model(self) -> str:
        return self.openai_model


settings = Settings()
