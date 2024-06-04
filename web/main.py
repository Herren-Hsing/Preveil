from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import mysql.connector
from flask_session import Session
import os
import hashlib
from werkzeug.utils import secure_filename
import random
import string
import json
import pandas as pd
import re
import subprocess
import shutil
import threading
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = 'uploads'

Session(app)
socketio = SocketIO(app)
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'private',
    'port': 3306
}

def connect_db():
    try:
        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            port=db_config['port']
        )
        if connection.is_connected():
            print("Successfully connected to the database")
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

@app.route('/download/<invite_code>', methods=['GET'])
def download_file(invite_code):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], invite_code, f"{invite_code}_result.csv")
    if os.path.exists(file_path):
        return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], invite_code), f"{invite_code}_result.csv", as_attachment=True)
    else:
        return jsonify({"success": False, "message": "File not found"}), 404

def execute_command(command, invite_code):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        
        with process.stdout as pipe:
            for line in pipe:
                print(line, end='', flush=True)
        
        process.wait()
        
        if process.returncode == 0:
            print("Command executed successfully")
            result_file_path = os.path.join('uploads', invite_code, 'result.txt')
            if os.path.exists(result_file_path):
                with open(result_file_path, 'r') as file:
                    error_value = file.read().strip()
                socketio.emit('command_status', {'status': 'success', 'message': 'Command executed successfully', 'error_value': error_value})
            else:
                socketio.emit('command_status', {'status': 'success', 'message': 'Command executed successfully', 'error_value': 'File not found'})
        else:
            print("Command execution failed")
            socketio.emit('command_status', {'status': 'error', 'message': 'Command execution failed'})
    except Exception as e:
        print(f"An error occurred while executing the command: {str(e)}")
        socketio.emit('command_status', {'status': 'error', 'message': f'An error occurred: {str(e)}'})

@app.route('/get_data', methods=['POST'])
def get_data():
    invite_code = request.json.get('invite_code')
    
    if not invite_code:
        return jsonify({"success": False, "message": "Invite code is required"}), 400

    command = f"""
    cd ../Programs/Source/ &&
    python mst.py --dataset ../../web/uploads/{invite_code}/{invite_code}.csv \
                --domain ../../web/uploads/{invite_code}/{invite_code}.json \
                --save ../../web/uploads/{invite_code}/{invite_code}_result.csv \
                --csv_path1 ../../web/uploads/{invite_code}/{invite_code}_0.csv \
                --json_path1 ../../web/uploads/{invite_code}/{invite_code}_0.json \
                --csv_path2 ../../web/uploads/{invite_code}/{invite_code}_1.csv \
                --json_path2 ../../web/uploads/{invite_code}/{invite_code}_1.json \
                --result_value ../../web/uploads/{invite_code}/result.txt &&
    cd ../../web/
    """

    print(command)

    threading.Thread(target=execute_command, args=(command, invite_code)).start()
        
    
    
    return jsonify({"success": True, "message": "Command is being executed"}), 200

def calculate_range(csv_file, json_file):
    df = pd.read_csv(csv_file)
    range_df = df.apply(lambda x: x.max() - x.min() + 1)
    range_dict = range_df.to_dict()
    with open(json_file, 'w') as f:
        json.dump(range_dict, f, indent=4)
        
@app.route('/')
def home():
    template_path = os.path.join(app.root_path, 'templates', 'index.html')
    app.logger.info(f'Looking for template at: {template_path}')
    if not os.path.exists(template_path):
        app.logger.error('Template file not found.')
        return 'Template file not found', 500
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        connection = connect_db()
        if connection is None:
            return "Failed to connect to the database. Please try again later."

        try:
            cursor = connection.cursor(dictionary=True)
            if role == 'uploader':
                cursor.execute("SELECT * FROM uploader WHERE account = %s AND password = %s", (username, password))
                user = cursor.fetchone()
                if user:
                    session['user_id'] = user['id']
                    session['role'] = 'uploader'
                    cursor.close()
                    connection.close()
                    return '/upload'
                else:
                    cursor.close()
                    connection.close()
                    return "Invalid credentials. Please try again."
            elif role == 'user':
                cursor.execute("SELECT * FROM user WHERE account = %s AND password = %s", (username, password))
                user = cursor.fetchone()
                if user:
                    session['user_id'] = user['id']
                    session['role'] = 'user'
                    cursor.close()
                    connection.close()
                    return '/query'
                else:
                    cursor.close()
                    connection.close()
                    return "Invalid credentials. Please try again."
        except mysql.connector.Error as err:
            return f"Database query failed: {err}"
    return render_template('login.html')


def calculate_file_hash(file):
    hasher = hashlib.md5()
    buf = file.read(65536)
    while len(buf) > 0:
        hasher.update(buf)
        buf = file.read(65536)
    file.seek(0)  # Reset file pointer to the beginning after reading
    return hasher.hexdigest()

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session or session.get('role') != 'uploader':
        return jsonify({"status": "error", "message": "Please log in as an uploader to access this page."})

    if request.method == 'POST':
        invite_code = request.form['invite_code']
        file = request.files['file']
        file_hash = calculate_file_hash(file)
        connection = connect_db()
        if connection is None:
            return jsonify({"status": "error", "message": "Failed to connect to the database. Please try again later."})

        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM files WHERE file_hash = %s and invite_code = %s", (file_hash, invite_code,))
            duplicate_file = cursor.fetchone()
            if duplicate_file:
                return jsonify({"status": "error", "message": "Duplicate file. This file has already been uploaded."})

            cursor.execute("SELECT * FROM invite_codes WHERE invite_code = %s", (invite_code,))
            invite = cursor.fetchone()
            if invite:
                reference_count = invite['reference_count']
                new_reference_count = reference_count + 1
                # Create the directory for the invite_code if it doesn't exist
                invite_code_folder = os.path.join(app.config['UPLOAD_FOLDER'], invite_code)
                if not os.path.exists(invite_code_folder):
                    os.makedirs(invite_code_folder)

                filename = f"{invite_code}_{reference_count}{os.path.splitext(file.filename)[1]}"
                file_path = os.path.join(invite_code_folder, secure_filename(filename))
                file.save(file_path)
                
                cursor.execute("INSERT INTO files (uploader_id, file_path, invite_code, file_hash) VALUES (%s, %s, %s, %s)", 
                               (session['user_id'], file_path, invite_code, file_hash))
                cursor.execute("UPDATE invite_codes SET reference_count = %s WHERE invite_code = %s", 
                               (new_reference_count, invite_code))
                connection.commit()

                cursor.close()
                connection.close()
                return jsonify({"status": "success", "message": "File uploaded successfully."})
            else:
                cursor.close()
                connection.close()
                return jsonify({"status": "error", "message": "Invalid invite code. Please try again."})
        except mysql.connector.Error as err:
            return jsonify({"status": "error", "message": f"Database query failed: {err}"})

    return render_template('upload.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        if password != confirm_password:
            return "Passwords do not match. Please try again."

        connection = connect_db()
        if connection is None:
            return "Failed to connect to the database. Please try again later."

        try:
            cursor = connection.cursor()
            if role == 'uploader':
                cursor.execute("SELECT * FROM uploader WHERE account = %s", (username,))
                existing_user = cursor.fetchone()
                if existing_user:
                    cursor.close()
                    connection.close()
                    return "Username already exists. Please choose another one."

                cursor.execute("INSERT INTO uploader (account, password) VALUES (%s, %s)", (username, password))
            elif role == 'user':
                cursor.execute("SELECT * FROM user WHERE account = %s", (username,))
                existing_user = cursor.fetchone()
                if existing_user:
                    cursor.close()
                    connection.close()
                    return "Username already exists. Please choose another one."

                cursor.execute("INSERT INTO user (account, password) VALUES (%s, %s)", (username, password))
            connection.commit()
            cursor.close()
            connection.close()
            return "User registered successfully."
        except mysql.connector.Error as err:
            return f"Database query failed: {err}"
    return render_template('signup.html')

@app.route('/query')
def query():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    return render_template('query.html')


@app.route('/verify_invite', methods=['POST'])
def verify_invite():
    invite_code = request.json.get('invite_code')
    
    if not invite_code:
        return jsonify({"success": False, "message": "Invite code is required"}), 400

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM invite_codes WHERE invite_code = %s", (invite_code,))
    invite = cursor.fetchone()

    if not invite:
        return jsonify({"success": False, "message": "Invite code does not exist"}), 400
    
    if invite['reference_count'] == 0:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    
    if invite['reference_count'] != 0:
        upload_folder = os.path.join('uploads', invite_code)
        if not os.path.exists(upload_folder):
            return jsonify({"success": False, "message": f"Directory {upload_folder} does not exist"}), 400
        
        pattern = re.compile(f"^{invite_code}_\d+\.csv$")
        csv_files = [f for f in os.listdir(upload_folder) if pattern.match(f)]
        
        if not csv_files:
            return jsonify({"success": False, "message": "No CSV files found in the directory"}), 400

        dfs = []
        for csv_file in csv_files:
            file_path = os.path.join(upload_folder, csv_file)
            df = pd.read_csv(file_path)
            dfs.append(df)
        
        merged_df = pd.concat(dfs, ignore_index=True)
        output_csv_file = os.path.join(upload_folder, f"{invite_code}.csv")
        merged_df.to_csv(output_csv_file, index=False)
        
        # Generate JSON file from the merged CSV
        output_json_file = os.path.join(upload_folder, f"{invite_code}.json")
        calculate_range(output_csv_file, output_json_file)
        
        for i in range(len(csv_files)):
            copied_json_file = os.path.join(upload_folder, f"{invite_code}_{i}.json")
            shutil.copy(output_json_file, copied_json_file)
        
    # If invite code is valid and not used
    return jsonify({"success": True, "message": "Invite code is valid"}), 200

def generate_unique_invite_code(cursor):
    while True:
        invite_code = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        cursor.execute("SELECT COUNT(*) FROM invite_codes WHERE invite_code = %s", (invite_code,))
        if cursor.fetchone()[0] == 0:
            return invite_code

@app.route('/invite', methods=['POST'])
def invite():
    if 'user_id' not in session or session.get('role') != 'user':
        return jsonify({"success": False, "message": "Unauthorized access"}), 403

    connection = connect_db()
    if connection is None:
        return jsonify({"success": False, "message": "Failed to connect to the database"}), 500

    try:
        cursor = connection.cursor()
        invite_code = generate_unique_invite_code(cursor)
        cursor.execute("INSERT INTO invite_codes (user_id, invite_code) VALUES (%s, %s)", 
                       (session['user_id'], invite_code))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"success": True, "invite_code": invite_code}), 200
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database query failed: {err}"}), 500

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=True)
    app.run(debug=True)
