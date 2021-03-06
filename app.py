# encoding=utf8
from flask import Flask, redirect, request, url_for, session, render_template, send_from_directory, jsonify, Response
from flask_oauth import OAuth

import sys
import json

reload(sys)
sys.setdefaultencoding('utf8')  # preventing ASCII error

GOOGLE_CLIENT_ID = '215535738644-fopbesd5dgmcelhcrocf3natuek8i5jo.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'lBdAIaXTCxR4-Dx8jR1dHdSa'
REDIRECT_URI = '/oauth2callback'

SECRET_KEY = 'development key for Vacation Management'
DEBUG = True

app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth()

google = oauth.remote_app('google',
                          base_url='https://www.google.com/accounts/',
                          authorize_url='https://accounts.google.com/o/oauth2/auth',
                          request_token_url=None,
                          request_token_params={'scope': 'https://www.googleapis.com/auth/userinfo.email',
                                                'response_type': 'code'},
                          access_token_url='https://accounts.google.com/o/oauth2/token',
                          access_token_method='POST',
                          access_token_params={'grant_type': 'authorization_code'},
                          consumer_key=GOOGLE_CLIENT_ID,
                          consumer_secret=GOOGLE_CLIENT_SECRET)


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory(app.static_folder + '/js/', path)


@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory(app.static_folder + '/css/', path)


@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory(app.static_folder + '/img/', path)


@app.route('/')
def index():
    access_token = session.get('access_token')
    if access_token is None:
        return redirect(url_for('login'))

    access_token = access_token[0]
    from urllib2 import Request, urlopen, URLError

    headers = {'Authorization': 'OAuth ' + access_token}
    req = Request('https://www.googleapis.com/oauth2/v1/userinfo',
                  None, headers)
    try:
        res = urlopen(req)
    except URLError, e:
        if e.code == 401:
            # Unauthorized - bad token
            session.pop('access_token', None)
            return redirect(url_for('login'))
        return res.read()
    data = res.read()
    data_json = json.loads(data)

    from vacman.account import Account
    Account(data_json['email']).isnewuser()
    usergroup = Account(data_json['email']).getuserstatus()
    if usergroup == 'pending':
        return 'You have no access for this page, and administrator have to approve your account first.'

    vacations = Account(data_json['email']).getuservacations()
    return render_template('index.html', account=data_json, usergroup=usergroup, vacations=vacations)


@app.route('/login')
def login():
    callback = url_for('authorized', _external=True)
    return google.authorize(callback=callback)


@app.route('/logout')
def logout():
    session.pop('access_token', None)
    return redirect(url_for('login'))


@app.route('/admin')
def secret_page():
    from vacman.admin import Admin
    access_token = session.get('access_token')
    if access_token is None:
        return redirect(url_for('login'))

    access_token = access_token[0]
    from urllib2 import Request, urlopen, URLError

    headers = {'Authorization': 'OAuth ' + access_token}
    req = Request('https://www.googleapis.com/oauth2/v1/userinfo',
                  None, headers)
    try:
        res = urlopen(req)
    except URLError, e:
        if e.code == 401:
            # Unauthorized - bad token
            session.pop('access_token', None)
            return redirect(url_for('login'))
        return res.read()
    data = res.read()
    data_json = json.loads(data)

    from vacman.account import Account
    usergroup = Account(data_json['email']).getuserstatus()

    if (usergroup != 'admin'):  # Backend check
        return ''

    from vacman.account import Account
    Account(data_json['email']).isnewuser()
    usergroup = Account(data_json['email']).getuserstatus()
    accounts = Admin().accounts_as_dict()
    requests = Admin().requests_as_dict()

    return render_template('admin.html', account=data_json, usergroup=usergroup, accounts=accounts, requests=requests)


@app.route('/request-vac', methods=['POST'])
def request_vac():
    access_token = session.get('access_token')
    if access_token is None:
        return redirect(url_for('login'))

    access_token = access_token[0]
    from urllib2 import Request, urlopen, URLError

    headers = {'Authorization': 'OAuth ' + access_token}
    req = Request('https://www.googleapis.com/oauth2/v1/userinfo',
                  None, headers)
    try:
        res = urlopen(req)
    except URLError, e:
        if e.code == 401:
            # Unauthorized - bad token
            session.pop('access_token', None)
            return redirect(url_for('login'))
        return res.read()
    data = res.read()
    data_json = json.loads(data)

    from vacman.account import Account
    usergroup = Account(data_json['email']).getuserstatus()

    if (usergroup == 'viewer' and usergroup == 'pending'):  # Backend check
        return ''
    else:
        from vacman.request_vacation import VacMan
        try:
            rv = VacMan(data_json['email'], request.form['date'])
            rv.request()
        except ValueError as err:
            return jsonify({"error": str(err)}), 400

        return ''


@app.route('/admin_request', methods=['POST'])
def admin_request():
    access_token = session.get('access_token')
    if access_token is None:
        return redirect(url_for('login'))

    access_token = access_token[0]
    from urllib2 import Request, urlopen, URLError

    headers = {'Authorization': 'OAuth ' + access_token}
    req = Request('https://www.googleapis.com/oauth2/v1/userinfo',
                  None, headers)
    try:
        res = urlopen(req)
    except URLError, e:
        if e.code == 401:
            # Unauthorized - bad token
            session.pop('access_token', None)
            return redirect(url_for('login'))
        return res.read()
    data = res.read()
    data_json = json.loads(data)

    from vacman.account import Account
    usergroup = Account(data_json['email']).getuserstatus()

    if (usergroup != 'admin'):  # Checking if admin sents the request
        return ''
    else:
        from vacman.admin import Admin
        try:
            if request.form['type'] == 'request_change':
                Admin().change_request(request.form['user'], request.form['date'], request.form['status'])
            else:
                Admin().change_user_info(request.form['user'], request.form['usergroup'])
        except ValueError as err:
            return jsonify({"error": str(err)}), 400

        return ''


@app.route(REDIRECT_URI)
@google.authorized_handler
def authorized(resp):
    access_token = resp['access_token']
    session['access_token'] = access_token, ''
    return redirect(url_for('index'))


@google.tokengetter
def get_access_token():
    return session.get('access_token')


def main():
    app.run()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
