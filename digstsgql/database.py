import sqlalchemy
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine



USER = "root"
PASSWORD = "insecure"
HOST = "db"
PORT = "5432"
NAME = "digstsgql"

DATABASE_URL = f"postgresql+psycopg://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}"


engine = create_async_engine(DATABASE_URL)
Session = async_sessionmaker(engine)



def run_upgrade(database_metadata: MetaData) -> None:
    # Create all tables in the metadata, ignoring tables already present in the
    # database. A proper migration tool, such as alembic, is more appropriate.
    # https://docs.sqlalchemy.org/en/20/tutorial/metadata.html#emitting-ddl-to-the-database
    engine = sqlalchemy.create_engine(DATABASE_URL)
    with engine.begin() as connection:
        database_metadata.create_all(connection)

