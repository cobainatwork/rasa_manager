import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 讓容器內 /app 或本機 backend/ 可被 import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.database.models import Base  # noqa: E402
import api.database.models  # noqa: F401, E402  # 確保所有 model 被載入至 metadata

config = context.config

# 從環境變數讀取 DATABASE_URL，覆寫 alembic.ini 的空白設定
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL 未設定，無法執行 alembic")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
