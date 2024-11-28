import asyncio
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import sqlalchemy
from sqlalchemy import ForeignKey
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from digstsgql.config import Settings


def run_upgrade(database_metadata: MetaData) -> None:
    """
    Create all tables in the metadata, ignoring tables already present in the database.

    A proper migration tool, such as alembic, is more appropriate.
    https://docs.sqlalchemy.org/en/20/tutorial/metadata.html#emitting-ddl-to-the-database
    """
    settings = Settings()
    engine = sqlalchemy.create_engine(settings.database.url)
    with engine.begin() as connection:
        database_metadata.create_all(connection)


class AsyncSessionWithLock(AsyncSession):
    """
    Each HTTP request/GraphQL query operates on a single database session,
    which cannot be used concurrently. To allow the usage of asyncio gather and
    tasks -- which is required to enable the dataloader pattern -- we have to
    add our own concurrency controls as close to the database as possible.

    The alternative to this is to use a separate session for each database
    query, but this provides an inconsistent view of the data across the
    GraphQL query.

    Copied from
    https://github.com/magenta-aps/os2mo/blob/cf34fae3889ebaca77609d6175321bf42d6f55fe/backend/mora/db/__init__.py#L80-L119
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.lock = asyncio.Lock()

        @asynccontextmanager
        async def with_lock():
            async with self.lock:
                yield

        # WARNING: It is very easy to introduce a deadlock by wrapping a method which
        # awaits another wrapped method. Check the superclass' implementation before
        # guarding a new method!
        methods = (
            "close",
            "commit",
            "delete",
            "execute",
            "flush",
            "get",
            "get_one",
            "invalidate",
            "merge",
            "refresh",
            "reset",
            "rollback",
            "scalar",
            "stream",
        )
        for method in methods:
            original = getattr(self, method)
            wrapped = with_lock()(original)
            setattr(self, method, wrapped)


def create_async_sessionmaker(database_url: str) -> async_sessionmaker:
    """Create the SQLAlchemy sessionmaker.

    This should be a singleton, but instantiation is deferred through a
    function call to allow passing the database URL from settings.
    """
    engine = create_async_engine(
        database_url,
        # echo=True,
    )
    session = async_sessionmaker(engine, class_=AsyncSessionWithLock)
    return session


class Base(DeclarativeBase):
    """Base class used for declarative class definitions."""


class Organisation(Base):
    __tablename__ = "organisation"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    brugervendtnoegle: Mapped[str | None]
    organisationsnavn: Mapped[str | None]

    # TODO: these should be ForeignKeys, but the related models are not part of
    # phase 1.
    # topenhed_id: Mapped[UUID | None]
    virksomhed_id: Mapped[UUID | None]
    myndighed_id: Mapped[UUID | None]


class Organisationenhed(Base):
    __tablename__ = "organisationenhed"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    brugervendtnoegle: Mapped[str | None]
    enhedsnavn: Mapped[str]

    organisation_id: Mapped[UUID | None] = mapped_column(ForeignKey("organisation.id"))
    overordnetenhed_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organisationenhed.id")
    )
