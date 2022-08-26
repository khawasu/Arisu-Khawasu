import config
from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import jsonify
import urllib
import json
import traceback

from common.device import Device
from common.khawasu import driver
from common.token import Token
from common.user import User, check_login

app = Flask(__name__)


# Just placeholder for root
@app.route('/')
def root():
    return "Your smart home is ready."


# Script must response 200 OK on this request
@app.route('/v1.0', methods=['GET', 'POST'])
def main_v10():
    return "OK"


# OAuth entry point
@app.route('/auth/', methods=['GET', 'POST'])
def auth():
    try:
        if request.method == 'GET':
            # Ask user for login and password
            return render_template('login.html')
        elif request.method == 'POST':
            if ("username" not in request.form or "password" not in request.form or "state" not in request.args
                    or "response_type" not in request.args
                    or request.args["response_type"] != "code"
                    or "client_id" not in request.args
                    or request.args["client_id"] != config.CLIENT_ID):

                if "username" in request.form:
                    request.user_id = request.form['username']
                print("invalid auth request")
                return "Invalid request", 400

            # Check login and password
            user = User.get_by_username(request.form["username"])
            if user is None or not check_login(user, request.form["password"]):
                print("invalid password")
                return render_template('login.html', login_failed=True)

            # Generate random code and remember this user and time
            token = Token.generate(user.username, Token.TOKEN_CODE_DEFAULT_LENGTH, request.args['state'])
            params = {'state': request.args['state'],
                      'code': token.value,
                      'client_id': config.CLIENT_ID}

            print("code generated")

            return redirect(request.args["redirect_uri"] + '?' + urllib.parse.urlencode(params))
    except Exception as ex:
        print(traceback.format_exc())
        return f"Error {type(ex).__name__}: {str(ex)}", 500


# OAuth, token request
@app.route('/token/', methods=['POST'])
def token():
    try:
        if ("client_secret" not in request.form
                or request.form["client_secret"] != config.CLIENT_SECRET
                or "client_id" not in request.form
                or request.form["client_id"] != config.CLIENT_ID
                or "code" not in request.form):
            print("invalid token request")
            return "Invalid request", 400

        token = Token.get_by_value(request.form["code"])

        # Check code
        if token is None:
            print("invalid code")
            return "Invalid code", 403

        # Check time
        if token.check_expired():
            print("code is too old")
            return "Code is too old", 403

        # Generate and save random token with username
        access_token = Token.generate(token.username, Token.TOKEN_ACCESS_DEFAULT_LENGTH)

        # Revoke code token
        token.revoke()

        print("access granted")

        # Return just token without any expiration time
        return jsonify({'access_token': access_token.value})
    except Exception as ex:
        print(traceback.format_exc())
        return f"Error {type(ex).__name__}: {str(ex)}", 500


# Function to retrieve token from header
def get_token():
    auth = request.headers.get('Authorization')
    if auth is None:
        return None

    parts = auth.split(' ', 2)
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    else:
        print(f"invalid token: {auth}")
        return None


# Method to revoke token
@app.route('/v1.0/user/unlink', methods=['POST'])
def unlink():
    try:
        access_token = Token.get_by_value(get_token())
        if access_token is None:
            return f"Error: Token not exists", 403

        access_token.revoke()
        print(f"token {access_token} revoked", access_token)

        return jsonify({'request_id': request.headers.get('X-Request-Id')})
    except Exception as ex:
        print(traceback.format_exc())
        return f"Error {type(ex).__name__}: {str(ex)}", 500


# Devices list
@app.route('/v1.0/user/devices', methods=['GET'])
def devices_list():
    try:
        access_token = Token.get_by_value(get_token())
        if access_token is None:
            return f"Error: Token not exists", 403

        request_id = request.headers.get('X-Request-Id')

        # Load user info
        user = User.get_by_username(access_token.username)
        if user is None:
            return f"Error: User not exists", 403

        # todo: add user devices
        result = {'request_id': request_id,
                  'payload': {'user_id': user.username, 'devices': [dev.get_row_object() for dev in Device.get_all()]}}

        return jsonify(result)
    except Exception as ex:
        print(traceback.format_exc())
        return f"Error {type(ex).__name__}: {str(ex)}", 500


# Method to query current device status
@app.route('/v1.0/user/devices/query', methods=['POST'])
def query():
    try:
        access_token = Token.get_by_value(get_token())
        if access_token is None:
            return f"Error: Token not exists", 403

        # Load user info
        user = User.get_by_username(access_token.username)
        if user is None:
            return f"Error: User not exists", 403

        request_id = request.headers.get('X-Request-Id')
        r = request.get_json()

        result = {'request_id': request_id, 'payload': {'devices': []}}

        for device in r["devices"]:
            device_obj = Device.get_by_id(device['id'])

            if device_obj is None:
                continue

            result['payload']['devices'].append(device_obj.query())

        return jsonify(result)
    except Exception as ex:
        print(traceback.format_exc())
        return f"Error {type(ex).__name__}: {str(ex)}", 500


# Method to execute some action with devices
@app.route('/v1.0/user/devices/action', methods=['POST'])
def action():
    try:
        access_token = Token.get_by_value(get_token())
        if access_token is None:
            return f"Error: Token not exists", 403

        # Load user info
        user = User.get_by_username(access_token.username)
        if user is None:
            return f"Error: User not exists", 403

        request_id = request.headers.get('X-Request-Id')
        r = request.get_json()

        result = {'request_id': request_id, 'payload': {'devices': []}}

        for device in r["payload"]["devices"]:
            device_obj = Device.get_by_id(device['id'])
            result['payload']['devices'].append(device_obj.action(device['capabilities']))

        return jsonify(result)
    except Exception as ex:
        print(traceback.format_exc())
        return f"Error {type(ex).__name__}: {str(ex)}", 500


app.run(host="192.168.1.194", port=1111)
