from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import random
import string
import hashlib
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

# Admin email configuration
ADMIN_EMAIL = "justinburgher@live.co.uk"

# Database initialization
def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect('solar_analyzer.db')
    cursor = conn.cursor()
    
    # Create email_verifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified BOOLEAN DEFAULT FALSE,
            analysis_count INTEGER DEFAULT 0
        )
    ''')
    
    # Create users table for tracking analysis limits
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            analysis_count INTEGER DEFAULT 0,
            verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

# Initialize database on startup
init_database()

# Battery options data
BATTERY_OPTIONS = [
    {"name": "Tesla Powerwall 3", "capacity": 13.5, "price_range": [7500, 8000]},
    {"name": "Enphase IQ Battery 5P", "capacity": 5.0, "price_range": [4500, 5000]},
    {"name": "LG Chem RESU10H", "capacity": 9.8, "price_range": [5500, 6000]},
    {"name": "Pylontech US3000C", "capacity": 3.55, "price_range": [1800, 2200]},
    {"name": "BYD Battery-Box Premium LVS", "capacity": 4.0, "price_range": [2500, 3000]},
    {"name": "Solax Triple Power T58", "capacity": 5.8, "price_range": [3500, 4000]},
    {"name": "Alpha ESS SMILE-B3", "capacity": 2.9, "price_range": [2000, 2500]},
    {"name": "Huawei LUNA2000", "capacity": 5.0, "price_range": [3000, 3500]},
    {"name": "SolarEdge Energy Bank", "capacity": 9.7, "price_range": [5000, 5500]},
    {"name": "Victron Energy Lithium", "capacity": 5.12, "price_range": [3500, 4000]},
    {"name": "Fronius Solar Battery", "capacity": 4.5, "price_range": [3000, 3500]},
    {"name": "Growatt ARK XH", "capacity": 2.56, "price_range": [1500, 2000]},
    {"name": "Goodwe Lynx Home U", "capacity": 3.3, "price_range": [2200, 2700]},
    {"name": "Solis RAI", "capacity": 5.1, "price_range": [3200, 3700]},
    {"name": "Moixa Smart Battery", "capacity": 2.0, "price_range": [2500, 3000]},
    {"name": "Powervault P4", "capacity": 4.1, "price_range": [3500, 4000]},
    {"name": "Sonnen ecoLinx", "capacity": 12.0, "price_range": [12000, 15000]},
    {"name": "Other", "capacity": 0, "price_range": [0, 0]}
]

def safe_float_convert(value, default=0.0):
    """Safely convert value to float, handling empty strings and None"""
    if value is None or value == '' or value == 'undefined':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int_convert(value, default=0):
    """Safely convert value to int, handling empty strings and None"""
    if value is None or value == '' or value == 'undefined':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def is_admin_email(email):
    """Check if email is admin email"""
    return email and email.lower() == ADMIN_EMAIL.lower()

def get_user_analysis_count(email):
    """Get user's current analysis count"""
    if is_admin_email(email):
        return 0  # Admin has unlimited analyses
    
    conn = sqlite3.connect('solar_analyzer.db')
    cursor = conn.cursor()
    cursor.execute('SELECT analysis_count FROM users WHERE email = ?', (email,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def increment_user_analysis_count(email):
    """Increment user's analysis count"""
    if is_admin_email(email):
        return  # Don't track admin analyses
    
    conn = sqlite3.connect('solar_analyzer.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (email, analysis_count, verified)
        VALUES (?, COALESCE((SELECT analysis_count FROM users WHERE email = ?), 0) + 1, 
                COALESCE((SELECT verified FROM users WHERE email = ?), FALSE))
    ''', (email, email, email))
    conn.commit()
    conn.close()

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

@app.route('/')
def home():
    return jsonify({
        "message": "Solar Quote Analyzer API",
        "version": "2.0",
        "endpoints": [
            "/api/battery-options",
            "/api/send-verification", 
            "/api/verify-email",
            "/api/analyze-quote",
            "/health"
        ]
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/battery-options')
def get_battery_options():
    return jsonify({"batteries": BATTERY_OPTIONS})

@app.route('/api/send-verification', methods=['POST'])
def send_verification():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({"success": False, "message": "Email is required"}), 400
        
        # Check if admin email
        if is_admin_email(email):
            print(f"🔑 Admin email detected: {email}")
            return jsonify({
                "success": True, 
                "message": "Admin verification bypassed",
                "admin": True
            })
        
        # Generate verification code
        code = generate_verification_code()
        
        # Store in database
        conn = sqlite3.connect('solar_analyzer.db')
        cursor = conn.cursor()
        
        # Delete any existing codes for this email
        cursor.execute('DELETE FROM email_verifications WHERE email = ?', (email,))
        
        # Insert new verification code
        cursor.execute('''
            INSERT INTO email_verifications (email, code, created_at, verified)
            VALUES (?, ?, ?, FALSE)
        ''', (email, code, datetime.now()))
        
        conn.commit()
        conn.close()
        
        # In production, you would send this via email
        # For testing, we'll log it
        print(f"🔑 VERIFICATION CODE for {email}: {code}")
        
        return jsonify({
            "success": True,
            "message": f"Verification code sent to {email}",
            "admin": False
        })
        
    except Exception as e:
        print(f"❌ Send verification error: {str(e)}")
        return jsonify({"success": False, "message": "Failed to send verification code"}), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()
        
        if not email or not code:
            return jsonify({"success": False, "message": "Email and code are required"}), 400
        
        # Check if admin email
        if is_admin_email(email):
            return jsonify({
                "success": True,
                "message": "Admin verification successful",
                "admin": True
            })
        
        # Verify code in database
        conn = sqlite3.connect('solar_analyzer.db')
        cursor = conn.cursor()
        
        # Check if code exists and is not expired (valid for 10 minutes)
        cursor.execute('''
            SELECT id FROM email_verifications 
            WHERE email = ? AND code = ? AND verified = FALSE
            AND created_at > datetime('now', '-10 minutes')
        ''', (email, code))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({"success": False, "message": "Invalid or expired verification code"}), 400
        
        # Mark as verified
        cursor.execute('''
            UPDATE email_verifications 
            SET verified = TRUE 
            WHERE email = ? AND code = ?
        ''', (email, code))
        
        # Update user as verified
        cursor.execute('''
            INSERT OR REPLACE INTO users (email, analysis_count, verified)
            VALUES (?, COALESCE((SELECT analysis_count FROM users WHERE email = ?), 0), TRUE)
        ''', (email, email))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Email verified successfully: {email}")
        
        return jsonify({
            "success": True,
            "message": "Email verified successfully",
            "admin": False
        })
        
    except Exception as e:
        print(f"❌ Verify email error: {str(e)}")
        return jsonify({"success": False, "message": "Verification failed"}), 500

@app.route('/api/analyze-quote', methods=['POST'])
def analyze_quote():
    try:
        data = request.get_json()
        print(f"📊 Received analysis request: {data}")
        
        # Extract and safely convert data
        system_size = safe_float_convert(data.get('system_size'))
        total_price = safe_float_convert(data.get('total_price'))
        has_battery = data.get('has_battery', False)
        battery_brand = data.get('battery_brand', '')
        battery_quantity = safe_int_convert(data.get('battery_quantity'), 1)
        battery_capacity = safe_float_convert(data.get('battery_capacity'))
        user_email = data.get('user_email', '').strip().lower()
        
        # Validate required fields
        if system_size <= 0:
            return jsonify({"success": False, "message": "Valid system size is required"}), 400
        
        if total_price <= 0:
            return jsonify({"success": False, "message": "Valid total price is required"}), 400
        
        # Check if admin
        is_admin = is_admin_email(user_email)
        print(f"👤 User: {user_email}, Admin: {is_admin}")
        
        # For non-admin users, check analysis limits
        if not is_admin and user_email:
            analysis_count = get_user_analysis_count(user_email)
            if analysis_count >= 3:
                return jsonify({
                    "success": False,
                    "message": "Analysis limit reached. Please upgrade for unlimited analyses.",
                    "upgrade_required": True
                }), 403
        
        # Calculate price per kW for solar panels only
        price_per_kw = total_price / system_size
        
        # Determine solar panel grade
        if price_per_kw < 1000:
            solar_grade = "A+"
            solar_verdict = "Excellent value"
        elif price_per_kw < 1200:
            solar_grade = "A"
            solar_verdict = "Very good value"
        elif price_per_kw < 1500:
            solar_grade = "B"
            solar_verdict = "Good value"
        elif price_per_kw < 2000:
            solar_grade = "C"
            solar_verdict = "Fair pricing"
        elif price_per_kw < 2500:
            solar_grade = "D"
            solar_verdict = "Expensive - consider getting more quotes"
        else:
            solar_grade = "F"
            solar_verdict = "Very expensive - definitely get more quotes"
        
        # Battery analysis
        battery_verdict = ""
        battery_grade = "N/A"
        
        if has_battery and battery_brand and battery_brand != "Other":
            # Find battery info
            battery_info = next((b for b in BATTERY_OPTIONS if b["name"] == battery_brand), None)
            if battery_info:
                total_battery_capacity = battery_info["capacity"] * battery_quantity
                battery_cost_estimate = sum(battery_info["price_range"]) / 2 * battery_quantity
                
                # Estimate battery portion of total price (rough calculation)
                estimated_solar_cost = system_size * 1000  # Assume £1000/kW for solar
                estimated_battery_portion = min(battery_cost_estimate, total_price - estimated_solar_cost)
                
                if estimated_battery_portion > 0:
                    battery_price_per_kwh = estimated_battery_portion / total_battery_capacity
                    
                    if battery_price_per_kwh < 400:
                        battery_grade = "A+"
                        battery_verdict = "Excellent battery value"
                    elif battery_price_per_kwh < 500:
                        battery_grade = "A"
                        battery_verdict = "Very good battery value"
                    elif battery_price_per_kwh < 600:
                        battery_grade = "B"
                        battery_verdict = "Good battery value"
                    elif battery_price_per_kwh < 700:
                        battery_grade = "C"
                        battery_verdict = "Fair battery pricing"
                    else:
                        battery_grade = "D"
                        battery_verdict = "Expensive battery"
        
        # Overall grade (combine solar and battery if applicable)
        overall_grade = solar_grade
        if has_battery and battery_grade != "N/A":
            # Simple grade combination logic
            grades = {"A+": 5, "A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
            grade_names = {5: "A+", 4: "A", 3: "B", 2: "C", 1: "D", 0: "F"}
            
            solar_score = grades.get(solar_grade, 0)
            battery_score = grades.get(battery_grade, 0)
            combined_score = (solar_score + battery_score) // 2
            overall_grade = grade_names.get(combined_score, "F")
        
        # Create verdict
        if has_battery and battery_verdict:
            verdict = f"{solar_verdict}. {battery_verdict}"
        else:
            verdict = solar_verdict
        
        # Increment analysis count for non-admin users
        if user_email and not is_admin:
            increment_user_analysis_count(user_email)
        
        # Get remaining analyses for response
        remaining_analyses = "unlimited" if is_admin else max(0, 3 - get_user_analysis_count(user_email))
        
        result = {
            "success": True,
            "grade": overall_grade,
            "verdict": verdict,
            "price_per_kw": round(price_per_kw, 0),
            "system_details": {
                "size": system_size,
                "total_price": total_price,
                "has_battery": has_battery
            },
            "admin": is_admin,
            "remaining_analyses": remaining_analyses
        }
        
        if has_battery and battery_brand != "Other":
            battery_info = next((b for b in BATTERY_OPTIONS if b["name"] == battery_brand), None)
            if battery_info:
                result["battery_details"] = {
                    "brand": battery_brand,
                    "quantity": battery_quantity,
                    "total_capacity": battery_info["capacity"] * battery_quantity
                }
        
        print(f"✅ Analysis completed - Grade: {overall_grade}, User: {user_email}, Admin: {is_admin}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Analysis error: {str(e)}")
        return jsonify({"success": False, "message": "Analysis failed"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

