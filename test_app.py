import os
from unittest.mock import patch

import httpx
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from faker import Faker
from pytest import fixture, mark
from structlog import get_logger

log = get_logger()

pytestmark = [mark.usefixtures("event_loop"), mark.asyncio]


@fixture(scope="session", autouse=True)
def faker():
    Faker.seed(0)
    return Faker()


@fixture(scope="session", autouse=True)
def environ():
    db_uri = os.environ["TEST_DATABASE_URI"]
    mock_environ = {"ALEMBIC_DATABASE_URI": db_uri, "DATABASE_URI": db_uri}

    with patch.dict("os.environ", mock_environ):
        yield mock_environ


@fixture(scope="session", autouse=True)
def db_migration(environ):
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")
    yield
    command.downgrade(alembic_config, "base")


@fixture
async def app():
    from app import app

    async with LifespanManager(app, startup_timeout=1, shutdown_timeout=1):
        yield app


@fixture
async def test_client(app):
    async with httpx.AsyncClient(app=app, base_url="http://localhost") as client:
        yield client


@fixture(autouse=True)
async def db():
    from databases import Database

    from app import user

    db = Database(os.environ["DATABASE_URI"])
    await db.connect()
    yield db
    await db.execute(user.delete())
    await db.disconnect()


@fixture
async def one_user(db):
    from app import User, user

    query = (
        user.insert().returning(user).values({"email": "bob@email.com", "name": "Bob"})
    )
    return User(**await db.fetch_one(query))


@fixture
async def twenty_users(db, faker):
    from app import User, user

    query = (
        user.insert()
        .returning(user)
        .values([{"email": faker.email(), "name": faker.name()} for _ in range(20)])
    )
    return [User(**row) for row in await db.fetch_all(query)]


async def test_health(test_client):
    res = await test_client.get("/health")
    assert res.status_code == 200


async def test_get_users(test_client, twenty_users):
    res = await test_client.get("/v1/users?offset=0&limit=15")

    assert res.status_code == 200
    json_body = res.json()

    data = json_body["data"]
    assert len(data) == 15

    meta = json_body["meta"]
    assert meta["next_url"] == "http://localhost/v1/users?offset=15&limit=15"


async def test_post_user_return_400_on_duplicate(test_client, one_user):
    res = await test_client.post(
        "/v1/users", json={"data": {"email": "bob@email.com", "name": "Bob"}}
    )
    assert res.status_code == 409


async def test_post_user(test_client, db):
    from app import User, user

    res = await test_client.post(
        "/v1/users", json={"data": {"email": "bob@email.com", "name": "Bob"}}
    )
    assert res.status_code == 201

    user_dict = res.json()["data"]
    user_id = user_dict["id"]

    new_user = User(**await db.fetch_one(user.select(user.c.id == user_id)))

    assert new_user.email == "bob@email.com"
    assert new_user.name == "Bob"
    assert new_user.created_at
