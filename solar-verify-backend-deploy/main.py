from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import random
import string
import sqlite3
import hashlib
import datetime
import re

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ADMIN CONFIGURATION
ADMIN_EMAILS = ['justinburgher@live.co.uk']  # Admin emails get unlimited access

def is_admin_email(email):
    """Check if email is an admin email"""
    return email.lower() in [admin.lower() for admin in ADMIN_EMAILS]

# Database setup
def init_db():
    try:
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        # Users table for email verification
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                email_hash TEXT UNIQUE NOT NULL,
                verification_code TEXT,
                is_verified BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                gdpr_consent BOOLEAN DEFAULT FALSE,
                consent_timestamp TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_verification_sent TEXT,
                verification_attempts INTEGER DEFAULT 0,
                analysis_count INTEGER DEFAULT 0
            )
        ''')
        
        # Analysis logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email_hash TEXT,
                system_size REAL,
                has_battery BOOLEAN,
                battery_brand TEXT,
                battery_quantity INTEGER,
                total_price REAL,
                grade TEXT,
                verdict TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")

# Initialize database on startup
init_db()

def hash_email(email):
    """Create a privacy-friendly hash of the email"""
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def validate_email(email):
    """Enhanced email validation"""
    if not email or '@' not in email:
        return False
    
    # Basic regex validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False
    
    # Block common fake domains
    fake_domains = ['test.com', 'example.com', 'fake.com', 'temp.com', '10minutemail.com']
    domain = email.split('@')[1].lower()
    if domain in fake_domains:
        return False
    
    return True

# Battery options with accurate pricing
BATTERY_OPTIONS = [
    {"brand": "Tesla Powerwall 3", "capacity": 13.5, "price_range": [7500, 8000]},
    {"brand": "Tesla Powerwall 2", "capacity": 13.5, "price_range": [6500, 7500]},
    {"brand": "Enphase IQ Battery 5P", "capacity": 5.0, "price_range": [3500, 4000]},
    {"brand": "Enphase IQ Battery 10", "capacity": 10.1, "price_range": [6000, 6500]},
    {"brand": "SolarEdge Home Battery", "capacity": 9.7, "price_range": [5500, 6000]},
    {"brand": "LG Chem RESU10H", "capacity": 9.8, "price_range": [5000, 5500]},
    {"brand": "LG Chem RESU16H", "capacity": 16.0, "price_range": [7000, 7500]},
    {"brand": "Pylontech US3000C", "capacity": 3.5, "price_range": [1800, 2200]},
    {"brand": "Pylontech US5000", "capacity": 4.8, "price_range": [2200, 2600]},
    {"brand": "BYD Battery-Box Premium LVS", "capacity": 4.0, "price_range": [2000, 2400]},
    {"brand": "Huawei LUNA2000", "capacity": 5.0, "price_range": [2800, 3200]},
    {"brand": "Alpha ESS SMILE-B3", "capacity": 2.9, "price_range": [1600, 2000]},
    {"brand": "Growatt ARK-2.5H-A1", "capacity": 2.5, "price_range": [1400, 1800]},
    {"brand": "Victron Energy Lithium", "capacity": 5.0, "price_range": [2500, 3000]},
    {"brand": "Sonnen eco 8", "capacity": 8.0, "price_range": [4500, 5000]},
    {"brand": "Powerwall Alternative", "capacity": 10.0, "price_range": [4000, 5000]},
    {"brand": "Generic Lithium Battery", "capacity": 5.0, "price_range": [2000, 3000]},
    {"brand": "Other (specify capacity)", "capacity": 0, "price_range": [0, 0]}
]

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "2.2.0-admin-testing-enabled",
        "admin_emails": len(ADMIN_EMAILS)
    })

@app.route('/api/battery-options', methods=['GET'])
def get_battery_options():
    return jsonify({"battery_options": BATTERY_OPTIONS})

@app.route('/api/send-verification', methods=['POST'])
def send_verification():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        gdpr_consent = data.get('gdpr_consent', False)
        
        if not validate_email(email):
            return jsonify({"error": "Invalid email address"}), 400
        
        if not gdpr_consent:
            return jsonify({"error": "GDPR consent is required"}), 400
        
        # Check if admin email
        admin_status = is_admin_email(email)
        if admin_status:
            logger.info(f"👑 ADMIN EMAIL DETECTED: {email}")
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        email_hash = hash_email(email)
        verification_code = generate_verification_code()
        current_time = datetime.datetime.now().isoformat()
        
        # Check rate limiting (3 attempts per hour)
        cursor.execute('''
            SELECT last_verification_sent, verification_attempts 
            FROM users WHERE email = ?
        ''', (email,))
        
        result = cursor.fetchone()
        if result:
            last_sent, attempts = result
            if last_sent:
                last_sent_time = datetime.datetime.fromisoformat(last_sent)
                time_diff = datetime.datetime.now() - last_sent_time
                
                if time_diff.total_seconds() < 3600 and attempts >= 3:  # 1 hour limit
                    conn.close()
                    return jsonify({"error": "Too many verification attempts. Please try again later."}), 429
        
        # Insert or update user
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (email, email_hash, verification_code, is_verified, is_admin, gdpr_consent, consent_timestamp, last_verification_sent, verification_attempts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT verification_attempts FROM users WHERE email = ?), 0) + 1)
        ''', (email, email_hash, verification_code, admin_status, admin_status, gdpr_consent, current_time, current_time, email))
        
        conn.commit()
        conn.close()
        
        # Log verification code (simulating email sending)
        logger.info(f"🔑 VERIFICATION CODE for {email}: {verification_code}")
        if admin_status:
            logger.info(f"👑 ADMIN ACCESS GRANTED for {email}")
        logger.info(f"📧 Email would be sent to: {email}")
        logger.info(f"📝 Subject: Solar✓erify - Verify Your Email Address")
        
        return jsonify({
            "message": "Verification code sent successfully",
            "is_admin": admin_status
        })
        
    except Exception as e:
        logger.error(f"❌ Send verification error: {str(e)}")
        return jsonify({"error": "Failed to send verification code"}), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        verification_code = data.get('verification_code', '').strip()
        
        if not email or not verification_code:
            return jsonify({"error": "Email and verification code are required"}), 400
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        email_hash = hash_email(email)
        
        # Check verification code
        cursor.execute('''
            SELECT verification_code, is_verified, is_admin
            FROM users WHERE email = ?
        ''', (email,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({"error": "User not found"}), 404
        
        stored_code, is_verified, is_admin = result
        
        if is_verified:
            conn.close()
            logger.info(f"✅ Email already verified for {email_hash}")
            return jsonify({
                "message": "Email verified successfully",
                "is_admin": is_admin
            })
        
        if stored_code != verification_code:
            conn.close()
            return jsonify({"error": "Invalid verification code"}), 400
        
        # Mark as verified
        cursor.execute('''
            UPDATE users SET is_verified = TRUE WHERE email = ?
        ''', (email,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Email verified for {email_hash}")
        if is_admin:
            logger.info(f"👑 ADMIN VERIFIED: {email}")
        
        return jsonify({
            "message": "Email verified successfully",
            "is_admin": is_admin
        })
        
    except Exception as e:
        logger.error(f"❌ Email verification error: {str(e)}")
        return jsonify({"error": "Verification failed"}), 500

@app.route('/api/analyze-quote', methods=['POST'])
def analyze_quote():
    try:
        data = request.get_json()
        
        # Extract form data
        system_size = float(data.get('system_size', 0))
        total_price = float(data.get('total_price', 0))
        has_battery = data.get('has_battery', False)
        battery_brand = data.get('battery_brand', '')
        battery_quantity = int(data.get('battery_quantity', 1))
        battery_capacity = float(data.get('battery_capacity', 0))
        user_email = data.get('user_email', '').strip().lower()
        
        # Validation
        if system_size <= 0 or total_price <= 0:
            return jsonify({"error": "Invalid system size or price"}), 400
        
        # Check user analysis limits (unless admin)
        analysis_count = 0
        is_admin = False
        user_verified = False
        
        if user_email:
            is_admin = is_admin_email(user_email)
            
            if not is_admin:  # Only check limits for non-admin users
                conn = sqlite3.connect('solar_verify.db')
                cursor = conn.cursor()
                
                email_hash = hash_email(user_email)
                cursor.execute('''
                    SELECT analysis_count, is_verified FROM users WHERE email = ?
                ''', (user_email,))
                
                result = cursor.fetchone()
                if result:
                    analysis_count, user_verified = result
                    
                    # Increment analysis count
                    cursor.execute('''
                        UPDATE users SET analysis_count = analysis_count + 1 WHERE email = ?
                    ''', (user_email,))
                    
                    conn.commit()
                    analysis_count += 1
                else:
                    # Anonymous user - first analysis
                    analysis_count = 1
                
                conn.close()
        else:
            # Anonymous user - first analysis
            analysis_count = 1
        
        # Calculate pricing components
        installation_cost = 2000  # Base installation cost
        
        # Battery cost calculation
        battery_cost = 0
        if has_battery and battery_brand and battery_brand != "Other (specify capacity)":
            battery_info = next((b for b in BATTERY_OPTIONS if b["brand"] == battery_brand), None)
            if battery_info:
                avg_battery_price = sum(battery_info["price_range"]) / 2
                battery_cost = avg_battery_price * battery_quantity
            else:
                # Fallback for unknown batteries
                battery_cost = 3000 * battery_quantity
        elif has_battery and battery_capacity > 0:
            # Custom battery capacity
            battery_cost = battery_capacity * 500  # £500 per kWh estimate
        
        # Solar panel cost (remaining after battery and installation)
        solar_cost = max(0, total_price - battery_cost - installation_cost)
        price_per_kw = solar_cost / system_size if system_size > 0 else 0
        
        # Grading logic for solar panels
        if price_per_kw <= 600:
            grade = 'A'
            verdict = "Excellent value for solar panels"
        elif price_per_kw <= 800:
            grade = 'B'
            verdict = "Good value for solar panels"
        elif price_per_kw <= 1000:
            grade = 'C'
            verdict = "Fair pricing for solar panels"
        elif price_per_kw <= 1200:
            grade = 'D'
            verdict = "Above average pricing"
        else:
            grade = 'F'
            verdict = "Overpriced - consider other quotes"
        
        # Enhanced verdict with battery consideration
        if has_battery and battery_cost > 0:
            if battery_brand == "Tesla Powerwall 3":
                if battery_cost <= 8000 * battery_quantity:
                    verdict += ". Excellent battery value"
                else:
                    verdict += ". Battery pricing is high"
            elif battery_cost <= 3000 * battery_quantity:
                verdict += ". Good battery pricing"
            else:
                verdict += ". Consider battery alternatives"
        
        # Calculate remaining analyses for non-admin users
        remaining_analyses = "unlimited" if is_admin else max(0, 3 - analysis_count)
        
        # Log analysis
        if user_email:
            try:
                conn = sqlite3.connect('solar_verify.db')
                cursor = conn.cursor()
                
                email_hash = hash_email(user_email)
                cursor.execute('''
                    INSERT INTO analysis_logs 
                    (user_email_hash, system_size, has_battery, battery_brand, battery_quantity, total_price, grade, verdict)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (email_hash, system_size, has_battery, battery_brand, battery_quantity, total_price, grade, verdict))
                
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"❌ Failed to log analysis: {str(e)}")
        
        logger.info(f"📊 Analysis completed: {system_size}kW, £{total_price}, Grade: {grade}")
        if is_admin:
            logger.info(f"👑 ADMIN ANALYSIS - Unlimited access")
        else:
            logger.info(f"📈 User analyses: {analysis_count}/3, Remaining: {remaining_analyses}")
        
        return jsonify({
            "grade": grade,
            "verdict": verdict,
            "price_per_kw": round(price_per_kw, 2),
            "system_details": {
                "system_size": system_size,
                "total_price": total_price,
                "has_battery": has_battery,
                "battery_info": f"{battery_quantity}x {battery_brand}" if has_battery else None,
                "total_capacity": f"{battery_quantity * (battery_capacity if battery_capacity > 0 else next((b['capacity'] for b in BATTERY_OPTIONS if b['brand'] == battery_brand), 0))}kWh" if has_battery else None
            },
            "analysis_count": analysis_count,
            "remaining_analyses": remaining_analyses,
            "is_admin": is_admin,
            "user_verified": user_verified
        })
        
    except Exception as e:
        logger.error(f"❌ Analysis error: {str(e)}")
        return jsonify({"error": "Analysis failed"}), 500

@app.route('/api/admin/reset-user', methods=['POST'])
def admin_reset_user():
    """Admin endpoint to reset user analysis count for testing"""
    try:
        data = request.get_json()
        admin_email = data.get('admin_email', '').strip().lower()
        target_email = data.get('target_email', '').strip().lower()
        
        if not is_admin_email(admin_email):
            return jsonify({"error": "Unauthorized - Admin access required"}), 403
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET analysis_count = 0 WHERE email = ?
        ''', (target_email,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"👑 ADMIN RESET: {admin_email} reset analysis count for {target_email}")
        
        return jsonify({"message": f"Analysis count reset for {target_email}"})
        
    except Exception as e:
        logger.error(f"❌ Admin reset error: {str(e)}")
        return jsonify({"error": "Reset failed"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

