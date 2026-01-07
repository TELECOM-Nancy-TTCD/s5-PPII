def test_utilisateurs_index_requires_login(client):
    resp = client.get('/utilisateurs', follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_utilisateurs_wrapper_redirect(auth_client):
    resp = auth_client.get('/utilisateurs', follow_redirects=False)
    assert resp.status_code in (302, 200, 403)

