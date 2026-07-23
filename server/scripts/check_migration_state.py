from sqlalchemy import create_engine, text

from app.core.config import settings

url = settings.database_url.replace("+asyncpg", "")
eng = create_engine(url)
with eng.connect() as c:
    ver = c.execute(text("select version_num from alembic_version")).fetchall()
    print("alembic_version", ver)
    tables = c.execute(
        text(
            "select tablename from pg_tables where schemaname='public' "
            "and tablename in ('commercial_proposals','proposal_builds','builds') "
            "order by 1"
        )
    ).fetchall()
    print("tables", tables)
    enums = c.execute(
        text(
            "select typname from pg_type where typname in "
            "('buildstatus','proposalsource','proposalstatus') order by 1"
        )
    ).fetchall()
    print("enums", enums)
