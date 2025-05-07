from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
import re
import os
import pickle
import pandas as pd
from urllib.parse import urlparse

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# --- MySQL Database Setup (Railway DB) ---
mysql_url = os.getenv('MYSQL_URL')
if not mysql_url:
    raise Exception("MYSQL_URL environment variable is not set")

url = urlparse(mysql_url)

app.config['MYSQL_HOST'] = url.hostname
app.config['MYSQL_USER'] = url.username
app.config['MYSQL_PASSWORD'] = url.password
app.config['MYSQL_DB'] = url.path.lstrip('/')
app.config['MYSQL_PORT'] = url.port

# Initialize MySQL
mysql = MySQL(app)

# --- Routes ---

# Home Page
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM new_users')  # Change here to use new_users table
        results = cursor.fetchall()
        cursor.close()
        return render_template('index.html', results=results)
    except Exception as e:
        print(f"Error: {e}")
        return "Database connection error."

# Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = ''
    if request.method == 'POST':
        full_name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if len(full_name) > 100:
            message = 'Full name too long! Max 100 characters.'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address!'
        elif not full_name or not password or not email:
            message = 'Please fill out the form completely!'
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM new_users WHERE email = %s', (email,))  # Change here to use new_users table
            account = cursor.fetchone()

            if account:
                message = 'Account already exists!'
            else:
                hashed_password = generate_password_hash(password)
                try:
                    cursor.execute(
                        'INSERT INTO new_users (full_name, email, password) VALUES (%s, %s, %s)',  # Change here to use new_users table
                        (full_name, email, hashed_password)
                    )
                    mysql.connection.commit()
                    flash('Signup successful. Please log in.', 'success')
                    return redirect(url_for('login'))
                except Exception as e:
                    mysql.connection.rollback()
                    print(f"Signup error: {e}")
                    message = 'Signup failed due to server error.'
            cursor.close()

    return render_template('signup.html', message=message)

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM new_users WHERE email = %s', (email,))  # Change here to use new_users table
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['userid']
            flash('Login successful.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Incorrect email/password.', 'error')

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# Prediction Page
@app.route('/predict', methods=['POST'])
def predict():
    try:
        form_data = {
            'satisfaction_level': float(request.form['satisfaction_level']),
            'last_evaluation': float(request.form['last_evaluation']),
            'number_project': int(request.form['number_project']),
            'average_monthly_hours': int(request.form['average_monthly_hours']),
            'time_spend_company': int(request.form['time_spend_company']),
            'work_accident': int(request.form['work_accident']),
            'promotion_last_5years': int(request.form['promotion_last_5years']),
            'Department': int(request.form['Department']),
            'salary': int(request.form['salary']),
        }

        model_path = os.path.join(os.path.dirname(__file__), 'final_prediction.pkl')
        with open(model_path, 'rb') as model_file:
            model = pickle.load(model_file)

        input_data = pd.DataFrame([form_data])
        input_data.columns = model.feature_names_in_

        prediction = model.predict(input_data)[0]
        message = "\u26a0\ufe0f Employee likely to Leave" if prediction == 1 else "\u2705 Employee likely to Stay"

        return render_template('result.html', predict=prediction, message=message)

    except Exception as e:
        print(f"Prediction error: {e}")
        flash('Prediction error. Please try again.', 'error')
        return redirect(url_for('index'))

# --- Main ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
