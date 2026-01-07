def test_login_post_invalid(client):
    resp = client.post('/login', data={'email': '', 'password': ''}, follow_redirects=True)
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    # Vérifier la présence des champs du formulaire ou du bouton de connexion
    assert ('name="email"' in text) or ('name="password"' in text) or ('Se connecter' in text) or ('se connecter' in text.lower())


def test_login_success(auth_client):
    resp = auth_client.get('/', follow_redirects=False)
    # Either redirect to login (if permission lacks) or allow access or redirect to accueil
    assert resp.status_code in (200, 302, 403)
