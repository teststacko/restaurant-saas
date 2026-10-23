
import os

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

from app import config


EXPECTED_TEST_DATABASE = "restaurant_test"
EXPECTED_TEST_USER = "neondb_owner"


@pytest.fixture(scope="session")
def owner_url():
    config.load_dotenv()

    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEST_DATABASE_URL is not set.")

    params = conninfo_to_dict(url)

    if params.get("dbname") != EXPECTED_TEST_DATABASE:
        pytest.fail(
            f"Refusing to wipe unexpected database: "
            f"{params.get('dbname')!r}"
        )

    if params.get("user") != EXPECTED_TEST_USER:
        pytest.fail(
            f"Refusing to wipe database using unexpected role: "
            f"{params.get('user')!r}"
        )

    host = params.get("host", "")
    if not host.endswith(".neon.tech"):
        pytest.fail("Refusing to wipe an unrecognized database host.")

    return url


@pytest.fixture
def clean_db(owner_url):
    with psycopg.connect(owner_url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")

    return owner_url
