from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Set up the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Connect to the database
def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',  # Your XAMPP MySQL password
        database='sitin'
    )
    return connection

# User class to handle user sessions
class User(UserMixin):
    def __init__(self, id, email, user_type, course, level, firstname=None, lastname=None):
        self.id = id
        self.email = email
        self.user_type = user_type
        self.course = course
        self.level = level
        self.firstname = firstname
        self.lastname = lastname


@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM USERS WHERE IDNO = %s", (user_id,))
    user_data = cursor.fetchone()
    connection.close()
    if user_data:
        return User(
            id=user_data['IDNO'], 
            email=user_data['EMAIL'], 
            user_type=user_data['USER_TYPE'],
            course=user_data['COURSE'],
            level=user_data['LEVEL'],
            firstname=user_data['FIRSTNAME'],  # Added firstname
            lastname=user_data['LASTNAME']     # Added lastname
        )
    return None


# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Capture the data from the form
        idno = request.form['idno']
        lastname = request.form['lastname']
        middlename = request.form['middlename']
        firstname = request.form['firstname']
        course = request.form['course']
        level = request.form['level']
        email = request.form['email']
        password = request.form['password'] 
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('register'))

        # Validate that the middle name is a single uppercase letter
        if len(middlename) != 1 or not middlename.isupper():
            flash("Middle name must be a single uppercase letter.", "danger")
            return redirect(url_for('register'))

        # Check if the ID number or email already exists
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE idno = %s", (idno,))
        existing_idno = cursor.fetchone()
        if existing_idno:
            flash("This ID number is already registered.", "danger")
            return redirect(url_for('register'))

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_email = cursor.fetchone()
        if existing_email:
            flash("This email is already registered.", "danger")
            return redirect(url_for('register'))

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        try:
            # Insert data into the database
            query = """
                INSERT INTO users (idno, lastname, middlename, firstname, course, level, email, password, user_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'STUDENT')
            """
            cursor.execute(query, (idno, lastname, middlename, firstname, course, level, email, hashed_password))
            connection.commit()
            flash("Registration successful!", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash("An error occurred: " + str(e), "danger")
            return render_template('register.html')

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        idno = request.form['idno']
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM USERS WHERE IDNO = %s", (idno,))
        user_data = cursor.fetchone()
        connection.close()

        if user_data and check_password_hash(user_data['PASSWORD'], password):
            # Ensure all required fields are passed to the User class
            user = User(
                id=user_data['IDNO'], 
                email=user_data['EMAIL'], 
                user_type=user_data['USER_TYPE'],
                course=user_data['COURSE'],  # Add the course field
                level=user_data['LEVEL'],
                firstname=user_data['FIRSTNAME'],  # Added firstname
                lastname=user_data['LASTNAME']     # Added lastname
            )
            login_user(user)
            if user.user_type == 'STAFF':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid ID number or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


# Admin Dashboard
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.user_type != 'STAFF':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')

# Student Dashboard
@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.user_type != 'STUDENT':
        return redirect(url_for('login'))
    return render_template('student_dashboard.html')

@app.route('/edit_info', methods=['POST'])
@login_required
def edit_info():
    firstname = request.form['firstname']
    lastname = request.form['lastname']
    email = request.form['email']
    course = request.form['course']
    level = request.form['level']
    password = request.form['password']

    connection = get_db_connection()
    cursor = connection.cursor()

    # If password is provided, hash it; otherwise, don't update the password
    if password:
        cursor.execute("""
            UPDATE users
            SET firstname = %s, lastname = %s, email = %s, course = %s, level = %s, password = %s
            WHERE idno = %s
        """, (firstname, lastname, email, course, level, generate_password_hash(password), current_user.id))
    else:
        cursor.execute("""
            UPDATE users
            SET firstname = %s, lastname = %s, email = %s, course = %s, level = %s
            WHERE idno = %s
        """, (firstname, lastname, email, course, level, current_user.id))

    connection.commit()
    connection.close()

    flash('Information updated successfully.', 'success')
    return redirect(url_for('student_dashboard'))

# Make Reservation Route
@app.route('/make_reservation', methods=['POST'])
@login_required
def make_reservation():
    session = request.form['session']

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO reservations (user_id, session)
        VALUES (%s, %s)
    """, (current_user.id, session))
    connection.commit()
    connection.close()

    flash('Reservation made successfully.', 'success')
    return redirect(url_for('student_dashboard'))

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)