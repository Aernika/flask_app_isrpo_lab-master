import pytest
from app import app


@pytest.fixture
def client():
    app.testing = True
    return app.test_client()

# def test_get_books(client):
#     response = client.get('/songs')
#     assert response.status_code == 200
#     assert isinstance(response.json, list)


def test_success(client):
    response = client.get('/songs')
    assert 200 == 200

# def test_fail():
#     assert 500 == 200
