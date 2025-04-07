from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta
import time

app = Flask(__name__)
app.secret_key = "your_secret_key"

def create_database():
    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            flight_id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_number TEXT NOT NULL,
            departure_airport TEXT NOT NULL,
            arrival_airport TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            status TEXT NOT NULL,
            country TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passengers (
            passenger_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            middle_name TEXT,
            last_name TEXT NOT NULL,
            birthday TEXT NOT NULL,
            passport_number TEXT UNIQUE NOT NULL,
            nationality TEXT NOT NULL,
            passport_issued_date TEXT NOT NULL,
            passport_expiry_date TEXT NOT NULL,
            flight_id INTEGER,
            FOREIGN KEY (flight_id) REFERENCES flights (flight_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trial (
            trial_id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date INTEGER NOT NULL,
            subscription_expiry INTEGER
        )
    ''')
    conn.commit()
    conn.close()

create_database()

def check_trial():
    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()
    cursor.execute("SELECT start_date, subscription_expiry FROM trial ORDER BY trial_id DESC LIMIT 1")
    trial = cursor.fetchone()
    conn.close()

    if not trial:
        return False

    start_date = datetime.fromtimestamp(trial[0])
    expiry_date = start_date + timedelta(days=90)
    now = datetime.now()

    if trial[1] and datetime.fromtimestamp(trial[1]) > now:
        return True

    return now <= expiry_date

def start_trial():
    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO trial (start_date) VALUES (?)", (int(time.time()),))
    conn.commit()
    conn.close()

def activate_subscription(subscription_key):
    valid_key = "1234"

    if subscription_key == valid_key:
        conn = sqlite3.connect('flights.db')
        cursor = conn.cursor()
        expiry_date = datetime.now() + timedelta(days=365)
        cursor.execute("UPDATE trial SET subscription_expiry = ? ORDER BY trial_id DESC LIMIT 1", (int(expiry_date.timestamp()),))
        conn.commit()
        conn.close()
        return True
    else:
        return False

@app.route('/')
def index():
    trial_status = None
    if check_trial():
        conn = sqlite3.connect('flights.db')
        cursor = conn.cursor()
        cursor.execute("SELECT subscription_expiry FROM trial ORDER BY trial_id DESC LIMIT 1")
        expiry = cursor.fetchone()
        conn.close()

        if expiry and expiry[0]:
            trial_status = "Subscription Active"
        else:
            conn = sqlite3.connect('flights.db')
            cursor = conn.cursor()
            cursor.execute("SELECT start_date FROM trial ORDER BY trial_id DESC LIMIT 1")
            start = cursor.fetchone()
            conn.close()

            start_date = datetime.fromtimestamp(start[0])
            expiry_date = start_date + timedelta(days=30)
            now = datetime.now()

            remaining_days = (expiry_date - now).days
            trial_status = f"Trial Active: {remaining_days} days remaining"
    else:
        trial_status = "Trial Expired"

    if not check_trial():
        return render_template('trial_expired.html')

    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flights")
    flights = cursor.fetchall()
    conn.close()

    formatted_flights = []
    for flight in flights:
        departure_time = datetime.fromisoformat(flight[4])
        arrival_time = datetime.fromisoformat(flight[5])
        formatted_flight = list(flight)
        formatted_flight[4] = departure_time.strftime('%Y-%m-%d %H:%M')
        formatted_flight[5] = arrival_time.strftime('%Y-%m-%d %H:%M')
        formatted_flights.append(formatted_flight)

    return render_template('index.html', flights=formatted_flights, trial_status=trial_status)

@app.route('/add_flight', methods=['GET', 'POST'])
def add_flight():
    if not check_trial():
        return render_template('trial_expired.html')

    if request.method == 'POST':
        flight_number = request.form['flight_number']
        departure_airport = request.form['departure_airport']
        arrival_airport = request.form['arrival_airport']
        departure_time = request.form['departure_time']
        arrival_time = request.form['arrival_time']
        status = request.form['status']
        country = request.form['country']

        conn = sqlite3.connect('flights.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO flights (flight_number, departure_airport, arrival_airport, departure_time, arrival_time, status, country) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (flight_number, departure_airport, arrival_airport, departure_time, arrival_time, status, country))
        conn.commit()
        conn.close()
        flash('Flight added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_flight.html')

@app.route('/add_passenger', methods=['GET', 'POST'])
def add_passenger():
    if not check_trial():
        return render_template('trial_expired.html')

    if request.method == 'POST':
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        last_name = request.form['last_name']
        birthday = request.form['birthday']
        passport_number = request.form['passport_number']
        nationality = request.form['nationality']
        passport_issued_date = request.form['passport_issued_date']
        passport_expiry_date = request.form['passport_expiry_date']

        conn = sqlite3.connect('flights.db')
        cursor = conn.cursor()

        try:
            sql = """INSERT INTO passengers (first_name, middle_name, last_name, birthday, passport_number, nationality, passport_issued_date, passport_expiry_date, flight_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            print("SQL Query:", sql)
            print("Parameters:", (first_name, middle_name, last_name, birthday, passport_number, nationality, passport_issued_date, passport_expiry_date, None))

            cursor.execute(sql,
                           (first_name, middle_name, last_name, birthday, passport_number, nationality, passport_issued_date, passport_expiry_date, None))
            conn.commit()
            conn.close()
            flash('Passenger added successfully!', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Passport number already exists.', 'danger')
            return render_template('add_passenger.html')
        except sqlite3.Error as e:
            flash(f'Database error: {e}', 'danger')
            return render_template('add_passenger.html')
    return render_template('add_passenger.html')

@app.route('/update_flight_status/<int:flight_id>', methods=['GET', 'POST'])
def update_flight_status(flight_id):
    if not check_trial():
        return render_template('trial_expired.html')

    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flights WHERE flight_id = ?", (flight_id,))
    flight = cursor.fetchone()

    if request.method == 'POST':
        status = request.form['status']
        cursor.execute("UPDATE flights SET status = ? WHERE flight_id = ?", (status, flight_id))
        conn.commit()
        conn.close()
        flash('Flight status updated successfully!', 'success')
        return redirect(url_for('index'))

    conn.close()
    return render_template('update_flight_status.html', flight=flight)

@app.route('/view_flight_status', methods=['GET', 'POST'])
def view_flight_status():
    if not check_trial():
        return render_template('trial_expired.html')

    flight = None
    if request.method == 'POST':
        flight_number = request.form['flight_number']

        conn = sqlite3.connect('flights.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM flights WHERE flight_number = ?", (flight_number,))
        flight = cursor.fetchone()
        conn.close()
    return render_template('view_flight_status.html', flight=flight)

@app.route('/view_passengers/<int:flight_id>')
def view_passengers(flight_id):
    if not check_trial():
        return render_template('trial_expired.html')

    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM passengers WHERE flight_id = ?", (flight_id,))
    passengers = cursor.fetchall()
    cursor.execute("SELECT flight_number FROM flights WHERE flight_id = ?", (flight_id,))
    flight = cursor.fetchone()
    conn.close()
    return render_template('view_passengers.html', passengers=passengers, flight=flight)

@app.route('/start_trial')
def start_trial_route():
    if check_trial():
        flash("Trial already started.", "info")
    else:
        start_trial()
        flash("Trial started successfully!", "success")
    return redirect(url_for('index'))

@app.route('/activate_subscription', methods=['GET', 'POST'])
def activate_subscription_route():
    if request.method == 'POST':
        subscription_key = request.form['subscription_key']
        if activate_subscription(subscription_key):
            flash("Subscription activated successfully!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid subscription key.", "danger")
    return render_template('activate_subscription.html')

@app.route('/update_flight/<int:flight_id>', methods=['GET', 'POST'])
def update_flight(flight_id):
    if not check_trial():
        return render_template('trial_expired.html')

    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        flight_number = request.form['flight_number']
        departure_airport = request.form['departure_airport']
        arrival_airport = request.form['arrival_airport']
        departure_time = request.form['departure_time']
        arrival_time = request.form['arrival_time']
        status = request.form['status']
        country = request.form['country']

        cursor.execute("""
            UPDATE flights
            SET flight_number = ?, departure_airport = ?, arrival_airport = ?,
                departure_time = ?, arrival_time = ?, status = ?, country = ?
            WHERE flight_id = ?
        """, (flight_number, departure_airport, arrival_airport, departure_time, arrival_time, status, country, flight_id))
        conn.commit()
        conn.close()
        flash('Flight details updated successfully!', 'success')
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM flights WHERE flight_id = ?", (flight_id,))
    flight = cursor.fetchone()
    conn.close()

    if flight:
        return render_template('update_flight.html', flight=flight)
    else:
        flash('Flight not found.', 'danger')
        return redirect(url_for('index'))

@app.route('/update_passenger/<int:passenger_id>', methods=['GET', 'POST'])
def update_passenger(passenger_id):
    if not check_trial():
        return render_template('trial_expired.html')

    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        last_name = request.form['last_name']
        birthday = request.form['birthday']
        passport_number = request.form['passport_number']
        nationality = request.form['nationality']
        passport_issued_date = request.form['passport_issued_date']
        passport_expiry_date = request.form['passport_expiry_date']

        try:
            cursor.execute("""
                UPDATE passengers
                SET first_name = ?, middle_name = ?, last_name = ?, birthday = ?,
                    passport_number = ?, nationality = ?, passport_issued_date = ?,
                    passport_expiry_date = ?
                WHERE passenger_id = ?
            """, (first_name, middle_name, last_name, birthday, passport_number, nationality,
                  passport_issued_date, passport_expiry_date, passenger_id))
            conn.commit()
            flash('Passenger details updated successfully!', 'success')
            return redirect(url_for('view_passengers', flight_id=request.args.get('flight_id')))

        except sqlite3.IntegrityError:
            flash('Passport number already exists.', 'danger')
            return render_template('update_passenger.html', passenger=passenger, flight_id = request.args.get('flight_id'))

        finally:
            conn.close()

    cursor.execute("SELECT * FROM passengers WHERE passenger_id = ?", (passenger_id,))
    passenger = cursor.fetchone()
    conn.close()

    if passenger:
        return render_template('update_passenger.html', passenger=passenger, flight_id = request.args.get('flight_id'))
    else:
        flash('Passenger not found.', 'danger')
        return redirect(url_for('index'))

@app.route('/delete_passenger/<int:passenger_id>/<int:flight_id>')
def delete_passenger(passenger_id, flight_id):
    if not check_trial():
        return render_template('trial_expired.html')

    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM passengers WHERE passenger_id = ?", (passenger_id,))
    conn.commit()
    conn.close()
    flash('Passenger deleted successfully!', 'success')
    return redirect(url_for('view_passengers', flight_id=flight_id))

@app.route('/add_passenger_to_flight/<int:flight_id>', methods=['GET', 'POST'])
def add_passenger_to_flight(flight_id):
    if not check_trial():
        return render_template('trial_expired.html')

    conn = sqlite3.connect('flights.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        passenger_ids = request.form.getlist('passenger_ids')
        for passenger_id in passenger_ids:
            cursor.execute("UPDATE passengers SET flight_id = ? WHERE passenger_id = ?", (flight_id, passenger_id))
        conn.commit()
        conn.close()
        flash('Passengers added to flight successfully!', 'success')
        return redirect(url_for('view_passengers', flight_id=flight_id))

    cursor.execute("SELECT * FROM passengers WHERE flight_id IS NULL")
    passengers = cursor.fetchall()
    conn.close()
    return render_template('add_passenger_to_flight.html', passengers=passengers, flight_id=flight_id)

if __name__ == '__main__':
    app.run(debug=True)