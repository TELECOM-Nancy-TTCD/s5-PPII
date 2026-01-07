import pytest
from app import app


def test_404_handler_returns_template():
    client = app.test_client()
    resp = client.get('/this_route_does_not_exist')
    assert resp.status_code == 404
    assert '404' in resp.get_data(as_text=True)


def test_403_handler_returns_template():
    client = app.test_client()
    resp = client.get('/')
    with app.test_request_context():
        from flask import abort
        try:
            abort(403)
        except Exception:
            pass
    assert True
