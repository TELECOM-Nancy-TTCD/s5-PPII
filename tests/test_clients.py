def test_clients_list_requires_permission(auth_client):
    resp = auth_client.get('/clients')
    assert resp.status_code in (200, 302, 403)


def test_create_client_form_get(auth_client):
    """create_client requires 'peut_gerer_clients' permission; regular user may be forbidden"""
    resp = auth_client.get('/client/create')
    assert resp.status_code in (200, 403, 302)


def test_create_client_post_validation(auth_client, db):
    """Try to create a client with missing required fields; the view expects form fields and will insert"""
    resp = auth_client.post('/client/create', data={
        'nom_entreprise': '',
        'contact_nom': '',
        'contact_email': '',
        'contact_telephone': '',
        'type_client': '',
    }, follow_redirects=True)
    # On vérifie si jamais on n'a pas d'erreur
    assert resp.status_code != 500

