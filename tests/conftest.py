import os

# Must be set before importing api so lifespan uses mock engine
os.environ["COUNCIL_TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from api import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def published_case_id(client):
    r = client.get("/cases")
    assert r.status_code == 200
    cases = r.json()
    assert cases, "No published cases available — check cases/ directory"
    return cases[0]["id"]
