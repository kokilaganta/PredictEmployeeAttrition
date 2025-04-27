import base64
import io
import os
import pickle
import re

import matplotlib
import matplotlib.pyplot as plt
import MySQLdb.cursors
import pandas as pd
from flask import Flask, redirect, render_template, request, session, url_for
from flask_mysqldb import MySQL

matplotlib.use('Agg')  # Use non-GUI backend to avoid Tcl_AsyncDelete error

app = Flask(__name__)

# Secret Key (For session management)
app.secret_key = 'xyzjkabc'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Gkokila@16'  # Update if needed
app.config['MYSQL_DB'] = 'user_management'

# Initialize MySQL
mysql = MySQL(app)

# Ensure static image directory exists
if not os.path.exists("static/images"):
    os.makedirs("static/images")

# ------------------ Login Route ------------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cursor.fetchone()
        cursor.close()  # Close cursor after use

        if user:
            session['loggedin'] = True
            session['userid'] = user.get('userid')
            session['name'] = user.get('full_name')
            session['email'] = user.get('email')
            return redirect(url_for('index'))  # Redirect to index page after login
        else:
            message = 'Incorrect email/password!'

    return render_template('login.html', message=message)

# ------------------ Logout Route ------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ------------------ Signup Route ------------------
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
                cursor.execute(
                    'INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)',
                    (full_name, email, password)
                )
                mysql.connection.commit()
                return redirect(url_for('login'))

        except MySQLdb.Error as e:
            print(f"MySQL error: {e}")
        finally:
            cursor.close()

    return render_template('signup.html', message=message)

# ------------------ Index Page Route ------------------
@app.route('/index')
def index():
    if 'loggedin' in session:
        return render_template('index.html', name=session.get('name', 'Guest'))
    return redirect(url_for('login'))


@app.route('/predict', methods=['POST'])
def predict():
    # 1. Get and process form data
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


    # 2. Load trained model
    with open('final_prediction.pkl', 'rb') as model_file:
        model = pickle.load(model_file)

    # 3. Create DataFrame
    input_data = pd.DataFrame([form_data])

    # Optional: Match model's expected column names
    input_data.columns = model.feature_names_in_

    # 4. Make prediction
    predict = model.predict(input_data)[0]
    
    msg = "⚠️ Employee is expected to Leave" if predict == 1 else "✅ Employee is expected to Stay"
    # --- Graphs ---

    # Graph 1 & 2: Workload (Bar + Curve)
    hours_fields = ['average_monthly_hours', 'number_project', 'time_spend_company']
    hours_values = input_data[hours_fields].iloc[0]

    # Bar Graph
    plt.figure(figsize=(6, 4))
    plt.bar(hours_fields, hours_values, color='coral')
    plt.title("Employee Workload - Bar Graph")
    plt.tight_layout()
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png')
    buf1.seek(0)
    hours_bar = base64.b64encode(buf1.read()).decode('utf-8')
    plt.close()

    # Curve Graph
    plt.figure(figsize=(6, 4))
    plt.plot(hours_fields, hours_values, marker='o', color='purple')
    plt.title("Employee Workload - Curve Graph")
    plt.tight_layout()
    buf2 = io.BytesIO()
    plt.savefig(buf2, format='png')
    buf2.seek(0)
    hours_curve = base64.b64encode(buf2.read()).decode('utf-8')
    plt.close()

    # Graph 3 & 4: Ratings (Bar + Curve)
    norm_fields = ['satisfaction_level', 'last_evaluation']
    norm_values = input_data[norm_fields].iloc[0]

    # Bar Graph
    plt.figure(figsize=(6, 4))
    plt.bar(norm_fields, norm_values, color='skyblue')
    plt.title("Employee Ratings - Bar Graph")
    plt.tight_layout()
    buf3 = io.BytesIO()
    plt.savefig(buf3, format='png')
    buf3.seek(0)
    ratings_bar = base64.b64encode(buf3.read()).decode('utf-8')
    plt.close()

    # Curve Graph
    plt.figure(figsize=(6, 4))
    plt.plot(norm_fields, norm_values, marker='o', color='green')
    plt.title("Employee Ratings - Curve Graph")
    plt.tight_layout()
    buf4 = io.BytesIO()
    plt.savefig(buf4, format='png')
    buf4.seek(0)
    ratings_curve = base64.b64encode(buf4.read()).decode('utf-8')
    plt.close()

    # 5. Render result.html
    return render_template("result.html",
                           
                           predict=predict,
                           message=msg,
                           hours_bar=hours_bar,
                           hours_curve=hours_curve,
                           ratings_bar=ratings_bar,
                           ratings_curve=ratings_curve)


# @app.route('/result', methods=['POST'])
# ------------------ Run the App ------------------
# if __name__ == '__main__':
#     app.run(debug=True)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
