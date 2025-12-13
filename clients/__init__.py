from flask import Blueprint, request, render_template
from flask_login import login_required

from tools import get_db

clients_bp = Blueprint('clients', __name__, template_folder="templates/interactions")

@clients_bp.route('/api/clients')
@login_required
def api_clients():
    db = get_db()
    clients = db.get_all_clients()
    # Transform clients to list of dicts to make it JSON serializable
    clients_list = [client.to_dict() for client in clients]
    return {"clients": clients_list}, 200