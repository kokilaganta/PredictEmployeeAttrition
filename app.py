from flask import Flask, redirect, render_template, request, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb
from flask_mysqldb import MySQL
import re
import pickle
import pandas as pd
import base64
import io
import matplotlib.pyplot as plt
from urllib.parse import urlparse
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Needed for session management

# Get MySQL URL from environment variables
mysql_url = os.getenv('MYSQL_URL', 'mysql://root:jsQSqZZuPRkTWmickRoBQYLmlxCVrKvt@mainline.proxy.rlwy.net:29593/railway')

# Parse the URL to extract connection details
url = urlparse(mysql_url)

print(f"Host: {url.hostname}, Port: {url.port}, User: {url.username}, Database: {url.path}")
# Parse the URL to extract connection details

# Configure Flask MySQL
app.config['MYSQL_HOST'] = url.hostname
app.config['MYSQL_USER'] = url.username
app.config['MYSQL_PASSWORD'] = url.password
app.config['MYSQL_DB'] = url.path[1:]  # Extract database name
app.config['MYSQL_PORT'] = url.port

# Initialize MySQL
mysql = MySQL(app)

# Connect to MySQLdb directly (if needed)
connection = MySQLdb.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    passwd=app.config['MYSQL_PASSWORD'],
    db=app.config['MYSQL_DB'],
    port=app.config['MYSQL_PORT']
)

@app.route('/')
def index():
    try:
        # Create a cursor object to interact with the database
        cursor = mysql.connection.cursor()

        # Execute query to fetch all users
        cursor.execute('SELECT * FROM users')
        
        # Fetch all results
        results = cursor.fetchall()
        
        # Close the cursor
        cursor.close()

        # Return the results to be displayed in a template
        return render_template('index.html', results=results)
    
    except Exception as e:
        # Handle any errors (e.g., database connection issues)
        print(f"Error occurred: {e}")
        return "There was an error retrieving the data."

# Running the app
if __name__ == '__main__':
    app.run(debug=True)

# Signup Route
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    message = ''
    if request.method == 'POST':
        full_name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        try:
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            account = cursor.fetchone()

            if account:
                message = 'Account already exists!'
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                message = 'Invalid email format!'
            elif not full_name or not password or not email:
                message = 'Please fill out the form!'
            else:
                hashed_password = generate_password_hash(password)
                cursor.execute(
                    'INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)',
                    (full_name, email, hashed_password)
                )
                mysql.connection.commit()

                # Log the user in after successful signup
                cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
                user = cursor.fetchone()
                session['user_id'] = user['id']  # Store user ID in session

                flash("Registration successful! You're now logged in.", "success")
                return redirect(url_for('index'))  # Redirect to home after signup

        except MySQLdb.Error as e:
            print(f"MySQL error: {e}")
            message = 'Database error, please try again later.'
        finally:
            cursor.close()

    return render_template('signup.html', message=message)

# Login Route
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Email and password are required", "error")
            return redirect(url_for('login'))

        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            cursor.close()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']  # Store user ID in session
                flash("Login successful!", "success")
                return redirect(url_for('index'))  # Redirect to home page

            else:
                flash("Invalid email or password", "error")

        except MySQLdb.Error as e:
            print(f"Database Error: {e}")
            flash("A database error occurred. Please try again later.", "error")

        except Exception as e:
            print(f"Error: {e}")
            flash("An unexpected error occurred. Please try again later.", "error")

    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    flash("You've been logged out", "info")
    return redirect(url_for('login'))

# Prediction Route
@app.route('/predict', methods=['POST'])
def predict():
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

    # Load trained model for prediction
    with open('final_prediction.pkl', 'rb') as model_file:
        model = pickle.load(model_file)

    input_data = pd.DataFrame([form_data])
    input_data.columns = model.feature_names_in_

    # Make prediction
    predict = model.predict(input_data)[0]
    msg = "⚠️ Employee is expected to Leave" if predict == 1 else "✅ Employee is expected to Stay"

    # Graphing logic (bar and curve plots for the features)
    # Add the graphs generation as done in your original code...

    return render_template("result.html", predict=predict, message=msg)

if __name__ == '__main__':
    app.run(debug=True)
