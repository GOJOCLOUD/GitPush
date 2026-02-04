from pathlib import Path
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ENV: str = Field(default="dev", description="运行环境: dev, staging, prod")
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    
    HOST: str = Field(default="127.0.0.1", description="服务监听地址")
    PORT: int = Field(default=8000, description="服务监听端口")
    
    CORS_ORIGINS: List[str] = Field(
        default=["tauri://localhost", "http://localhost:1420", "http://localhost:5173"],
        description="CORS允许的源",
    )
    
    HOME_DIR: Path = Field(default_factory=Path.home, description="用户主目录")
    WORK_DIR: Path = Field(default=Path.home(), description="工作目录")
    DATA_DIR: Path = Field(default=Path.home() / ".gitpush", description="数据目录")
    REPOS_DIR: Path = Field(default=Path.home() / ".gitpush" / "repos", description="仓库目录")
    
    DATABASE_URL: str = Field(default="sqlite:///./gitpush.db", description="数据库连接URL")
    
    JWT_SECRET: str = Field(default="your-secret-key-change-in-production", description="JWT密钥")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT算法")
    JWT_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7, description="JWT过期时间(分钟)")
    
    REDIS_URL: str = Field(default="", description="Redis连接URL")
    
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024, description="最大上传大小(字节)")
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("WORK_DIR", "DATA_DIR", "REPOS_DIR", mode="before")
    @classmethod
    def resolve_path(cls, v, info):
        if isinstance(v, str):
            v = Path(v)
        if not v.is_absolute():
            v = Path.home() / v
        return v
    
    def model_post_init(self, __context):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.REPOS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
