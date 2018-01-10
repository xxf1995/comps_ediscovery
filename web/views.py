
import flask
import pandas as pd
from flask import Flask, request
import json
app = Flask(__name__)
import os, sys
root_dir = os.path.dirname(os.getcwd())
sys.path.insert(0, root_dir)
from lib.dblib import Database

scenario = '401'

db = Database()
email_list = db.get_scenario(scenario)

# data = pd.read_pickle('../data/parsed/pickles/pickled_data_test.pickle')
# data['Relevant'] = '0'
#
# email_key = data[['ID','Date', 'From', 'To', 'Subject', 'Scenario']][:5000].copy()
# email_key_dict = email_key.to_dict(orient='index')
#
# #If there's a fast way to remove ID from v, we should do that here as well
# email_key_dict = {v['ID']:v for k, v in email_key_dict.items()}

def fake_data():
    data = {
        1 : ['the', 'but'],
        2 : ['a'],
        3 : ['for'],
        4 : ['this']
    }
    return data

@app.route("/topics")
def fake_data_endpoint():
    return flask.jsonify(fake_data())

@app.route("/datakey")
def data_key_endpoint():
    return flask.jsonify(email_list)

# @app.route("/data/<int:id>")
@app.route("/data/<id>")
def data_endpoint(id):
    # row = data.loc[id].to_dict()
    row = db.get_email_by_id(id, scenario=scenario)
    print(row)
    return flask.jsonify(row)

@app.route("/POC")
def poc():
    documents = fake_data()
    return flask.render_template('documentview.html', docs = documents)

@app.route('/feedback',methods=['GET','POST'])
def log_feedback():
    feedback = request.get_json()
    print(feedback)
    data.loc[data['ID'] == feedback['ID'], 'Relevant'] = feedback['Relevant']
    return '{"status": 200}\n'


app.run(debug=True)
