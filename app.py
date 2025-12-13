from flask import Flask,render_template,send_file
from flask import g

from app_conventions import conventions_bp

import sqlite3



app = Flask(__name__)

app.register_blueprint(conventions_bp)


#@app.teardown_appcontext
#def close_connection(exception):
#    db = getattr(g,'_database',None) 
#    if db is not None:
#        db.close()


@app.route('/data/<string:nom>')
def contenu(nom : str):
    print(nom)
    return send_file('./data/'+nom)

