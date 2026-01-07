def test_accueil_requires_login(client):
    # Without login, should redirect to login
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_login_page_get(client):
    resp = client.get('/login')
    assert resp.status_code == 200
    assert b"Se connecter" in resp.data or b"Login" in resp.data or b"Email" in resp.data

