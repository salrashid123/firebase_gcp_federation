import logging


from flask import Flask, render_template, request, Response,  send_from_directory, abort, redirect, jsonify, session,make_response
from flask_wtf.csrf import CSRFProtect
import requests

import time, datetime
from oauth2client.service_account import ServiceAccountCredentials
from google.auth.credentials import Credentials

import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth

app = Flask(__name__, static_url_path='')
app.secret_key = 'notasecret'
csrf = CSRFProtect(app)

PROJECT_ID="fb-federated"
PROJECT_NUMBER="5088031121211"

GCP_OIDC_STS_ENDPOINT         = "https://sts.googleapis.com/v1beta/token"
GCP_OIDC_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
GCP_AUDIENCE = "//iam.googleapis.com/projects/{}/locations/global/workloadIdentityPools/oidc-pool-1/providers/oidc-provider-1".format(PROJECT_NUMBER)
print(GCP_AUDIENCE)

@app.route('/public/<path:path>')
def send_file(path):
    return send_from_directory('public', path)

@app.route('/')
def index():
  return render_template('index.html')

@app.route('/_ah/health')
def health():
    return('ok')

@app.route('/portal', methods=["GET"])
def portal():
    return render_template('portal.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/logout')
def logout():
    response = make_response(redirect('/login'))
    response.set_cookie('session', expires=0)

    return render_template('logout.html')

@app.route('/verifyIdToken', methods = ['POST'])
def verifyIdToken():
    try:
      id_token = request.form['id_token']
      decoded_token = auth.verify_id_token(id_token)
      uid = decoded_token['uid']
      print("Verified User " + uid)

      # now exchange the id_token for a GCP federated token
      headers = {}
      payload = {
        'grant_type':'urn:ietf:params:oauth:grant-type:token-exchange',
        'audience': GCP_AUDIENCE,
        'subject_token_type': 'urn:ietf:params:oauth:token-type:jwt',
        'requested_token_type': 'urn:ietf:params:oauth:token-type:access_token',
        'scope': GCP_OIDC_CLOUD_PLATFORM_SCOPE,
        'subject_token': id_token
      }
      #print(id_token)
      s = requests.Session()
      response =  s.post(GCP_OIDC_STS_ENDPOINT,headers=headers,data=payload)
      #print(response.json())
      return jsonify({'uid': uid, 'project_id': PROJECT_ID, 'project_number': PROJECT_NUMBER, 'sts_token': response.json()['access_token'] })
    except auth.AuthError as e:
      logging.error(e.detail)
    except Exception as e:
      logging.error(e)
    response = make_response(redirect('/login'))
    response.set_cookie('session', expires=0)


if __name__ == '__main__':

    context = ('server.crt','server.key')
    cred = credentials.Certificate('../svc_account.json')
    default_app = firebase_admin.initialize_app(cred)    
    app.run(host='0.0.0.0', port=38080, threaded=True, ssl_context=context)
