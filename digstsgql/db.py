import sqlalchemy
from sqlalchemy import ForeignKey
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

USER = "root"
PASSWORD = "insecure"
HOST = "db"
PORT = "5432"
NAME = "digstsgql"

DATABASE_URL = f"postgresql+psycopg://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}"


engine = create_async_engine(DATABASE_URL)
Session = async_sessionmaker(engine)


def run_upgrade(database_metadata: MetaData) -> None:
    """
    Create all tables in the metadata, ignoring tables already present in the
    database. A proper migration tool, such as alembic, is more appropriate.
    https://docs.sqlalchemy.org/en/20/tutorial/metadata.html#emitting-ddl-to-the-database
    """
    engine = sqlalchemy.create_engine(DATABASE_URL)
    with engine.begin() as connection:
        database_metadata.create_all(connection)


class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "author"

    id: Mapped[int] = mapped_column(primary_key=True)

    first_name: Mapped[str]
    last_name: Mapped[str]

    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str]

    author_id: Mapped[int] = mapped_column(ForeignKey("author.id"))
    author: Mapped["Author"] = relationship(back_populates="books")
