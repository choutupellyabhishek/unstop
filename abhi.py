from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# Database setup
def init_db():
    with sqlite3.connect("train.db") as conn:
        cursor = conn.cursor()
        # Create seats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seats (
                seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                row_number INTEGER NOT NULL,
                seat_number INTEGER NOT NULL,
                is_booked BOOLEAN DEFAULT 0
            )
        """)
        
        # Populate seats if empty
        cursor.execute("SELECT COUNT(*) FROM seats")
        if cursor.fetchone()[0] == 0:
            for row in range(1, 13):  # Rows 1 to 11 have 7 seats, row 12 has 3 seats
                seat_count = 7 if row < 12 else 3
                for seat in range(1, seat_count + 1):
                    cursor.execute("INSERT INTO seats (row_number, seat_number) VALUES (?, ?)", (row, seat))
        conn.commit()

# Initialize the database
init_db()

@app.route('/book', methods=['POST'])
def book_seats():
    data = request.get_json()
    required_seats = data.get("seats")

    if not isinstance(required_seats, int) or required_seats < 1 or required_seats > 7:
        return jsonify({"error": "Invalid number of seats requested. You can book between 1 and 7 seats."}), 400

    with sqlite3.connect("train.db") as conn:
        cursor = conn.cursor()

        # Check for seats in the same row
        cursor.execute("""
            SELECT row_number, GROUP_CONCAT(seat_id) as seats, COUNT(*) as available
            FROM seats
            WHERE is_booked = 0
            GROUP BY row_number
            HAVING available >= ?
            ORDER BY row_number
        """, (required_seats,))

        row = cursor.fetchone()
        if row:
            row_number = row[0]
            seat_ids = list(map(int, row[1].split(",")))[:required_seats]
        else:
            # If not enough seats in one row, find nearby seats
            cursor.execute("SELECT seat_id FROM seats WHERE is_booked = 0 ORDER BY row_number, seat_number LIMIT ?", (required_seats,))
            seat_ids = [seat[0] for seat in cursor.fetchall()]

        if len(seat_ids) < required_seats:
            return jsonify({"error": "Not enough seats available."}), 400

        # Mark seats as booked
        cursor.executemany("UPDATE seats SET is_booked = 1 WHERE seat_id = ?", [(seat_id,) for seat_id in seat_ids])
        conn.commit()

    return jsonify({"message": "Seats booked successfully!", "seats": seat_ids})

@app.route('/seats', methods=['GET'])
def get_seat_status():
    with sqlite3.connect("train.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT row_number, seat_number, is_booked FROM seats ORDER BY row_number, seat_number")
        seats = cursor.fetchall()

    seat_map = {}
    for row_number, seat_number, is_booked in seats:
        if row_number not in seat_map:
            seat_map[row_number] = []
        seat_map[row_number].append({"seat_number": seat_number, "is_booked": bool(is_booked)})

    return jsonify(seat_map)

if __name__ == '__main__':
    app.run(debug=True)