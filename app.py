import os
from datetime import datetime
from typing import Generic, TypeVar
from urllib.parse import urlencode

from asyncpg.exceptions import UniqueViolationError
from databases import Database
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pkg_resources import get_distribution
from pydantic import BaseModel
from pydantic.generics import GenericModel
from sqlalchemy import MetaData, Table, create_engine
from structlog import get_logger

__version__ = get_distribution("devops-challenge").version

log = get_logger(__name__)

metadata = MetaData()
metadata.reflect(create_engine(os.environ["DATABASE_URI"]))
database = None
user: Table = Table("user", metadata, autoload=True)

app = FastAPI(title="API", version=__version__)


@app.get("/health")
async def health():
    return "OK"


@app.on_event("startup")
async def startup():
    global database
    database = Database(os.environ["DATABASE_URI"])
    await database.connect()
    log.info("startup")


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    log.info("shutdown")


async def with_db() -> Database:
    transaction = await database.transaction()

    try:
        yield database

    except Exception:  # pragma no cover
        await transaction.rollback()

    else:
        await transaction.commit()


T = TypeVar("T")


class Item(GenericModel, Generic[T]):
    data: T


class Meta(BaseModel):
    page_index: int
    next_url: str


class Collection(GenericModel, Generic[T]):
    data: list[T]
    meta: Meta


async def with_pagination(
    request: Request, offset: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    async def paginated_result(db, query) -> Collection[T]:
        page_index = offset / limit
        next_qs = urlencode({"offset": offset + limit, "limit": limit})
        next_url = f"{request.url_for('users-collection')}?{next_qs}"
        return Collection[T](
            data=await db.fetch_all(query.offset(offset).limit(limit)),
            meta={"page_index": page_index, "next_url": next_url},
        )

    return paginated_result


class User(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime


class NewUser(BaseModel):
    email: str
    name: str


@app.get("/v1/users", name="users-collection", response_model=Collection[User])
async def get_users(
    db: Database = Depends(with_db), paginated_result=Depends(with_pagination)
):
    return await paginated_result(db, user.select())


@app.post("/v1/users", response_model=Item[User], status_code=201)
async def post_users(item: Item[NewUser], db: Database = Depends(with_db)):
    query = user.insert().returning(user).values(item.data.dict())
    try:
        return {"data": await db.fetch_one(query)}
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail=exc.detail)
