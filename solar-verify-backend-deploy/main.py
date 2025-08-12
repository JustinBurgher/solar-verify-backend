
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import random
import string
import hashlib
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Admin email for unlimited access
ADMIN_EMAIL = "justinburgher@live.co.uk"

# Battery options with capacities
BATTERY_OPTIONS = [
    {"brand": "Tesla Powerwall 3 (13.5kWh)", "capacity": 13.5},
    {"brand": "Tesla Powerwall 2 (13.5kWh)", "capacity": 13.5},
    {"brand": "Enphase IQ Battery 5P (5kWh)", "capacity": 5.0},
    {"brand": "Enphase IQ Battery 10 (10.1kWh)", "capacity": 10.1},
    {"brand": "SolarEdge Home Battery (9.7kWh)", "capacity": 9.7},
    {"brand": "LG Chem RESU10H (9.8kWh)", "capacity": 9.8},
    {"brand": "LG Chem RESU16H (16kWh)", "capacity": 16.0},
    {"brand": "Pylontech US3000C (3.5kWh)", "capacity": 3.5},
    {"brand": "Pylontech US5000 (4.8kWh)", "capacity": 4.8},
    {"brand": "BYD Battery-Box Premium LVS (4kWh)", "capacity": 4.0},
    {"brand": "Huawei LUNA2000 (5kWh)", "capacity": 5.0},
    {"brand": "Alpha ESS SMILE-B3 (2.9kWh)", "capacity": 2.9},
    {"brand": "Growatt ARK-2.5H-A1 (2.5kWh)", "capacity": 2.5},
    {"brand": "Victron Energy Lithium (5kWh)", "capacity": 5.0},
    {"brand": "Sonnen eco 8 (8kWh)", "capacity": 8.0},
    {"brand": "Powerwall Alternative (10kWh)", "capacity": 10.0},
    {"brand": "Generic Lithium Battery (5kWh)", "capacity": 5.0},
    {"brand": "Other (specify capacity)", "capacity": 0}
]

def init_db():
    """Initialize the database"""
    try:
        conn = sqlite3.connect('email_verification.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                email_hash TEXT NOT NULL,
                verification_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified BOOLEAN DEFAULT FALSE,
                analysis_count INTEGER DEFAULT 0,
                gdpr_consent BOOLEAN DEFAULT FALSE,
                consent_timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {str(e)}")

def safe_float_convert(value, default=0.0):
    """Safely convert a value to float, handling empty strings and None"""
    if value is None or value == '' or value == 'undefined':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"⚠️ Could not convert '{value}' to float, using default {default}")
        return default

def safe_int_convert(value, default=1):
    """Safely convert a value to int, handling empty strings and None"""
    if value is None or value == '' or value == 'undefined':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"⚠️ Could not convert '{value}' to int, using default {default}")
        return default

def hash_email(email):
    """Create a hash of the email for privacy"""
    return hashlib.sha256(email.lower().encode()).hexdigest()

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def is_admin_email(email):
    """Check if email is admin"""
    return email.lower() == ADMIN_EMAIL.lower()

@app.route('/api/battery-options', methods=['GET'])
def get_battery_options():
    """Get available battery options"""
    try:
        return jsonify({"battery_options": BATTERY_OPTIONS})
    except Exception as e:
        logger.error(f"❌ Error getting battery options: {str(e)}")
        return jsonify({"error": "Failed to get battery options"}), 500

@app.route('/api/send-verification', methods=['POST'])
def send_verification():
    """Send email verification code"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        gdpr_consent = data.get('gdpr_consent', False)
        consent_timestamp = data.get('consent_timestamp', '')
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        # Check if admin
        if is_admin_email(email):
            logger.info(f"👑 Admin email detected: {email}")
            return jsonify({
                "message": "Admin verification bypassed",
                "is_admin": True
            })
        
        # Generate verification code
        verification_code = generate_verification_code()
        email_hash = hash_email(email)
        
        # Store in database
        conn = sqlite3.connect('email_verification.db')
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute('SELECT id, verified FROM email_verifications WHERE email_hash = ?', (email_hash,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            cursor.execute('''
                UPDATE email_verifications 
                SET verification_code = ?, created_at = CURRENT_TIMESTAMP, verified = FALSE
                WHERE email_hash = ?
            ''', (verification_code, email_hash))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO email_verifications 
                (email, email_hash, verification_code, gdpr_consent, consent_timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, email_hash, verification_code, gdpr_consent, consent_timestamp))
        
        conn.commit()
        conn.close()
        
        # In production, send actual email here
        logger.info(f"🔑 VERIFICATION CODE for {email}: {verification_code}")
        
        return jsonify({
            "message": "Verification code sent",
            "is_admin": False
        })
        
    except Exception as e:
        logger.error(f"❌ Send verification error: {str(e)}")
        return jsonify({"error": "Failed to send verification"}), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    """Verify email with code"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        verification_code = data.get('verification_code', '').strip()
        
        if not email or not verification_code:
            return jsonify({"error": "Email and verification code are required"}), 400
        
        # Check if admin
        if is_admin_email(email):
            logger.info(f"👑 Admin email verification bypassed: {email}")
            return jsonify({
                "message": "Admin verification successful",
                "is_admin": True
            })
        
        email_hash = hash_email(email)
        
        conn = sqlite3.connect('email_verification.db')
        cursor = conn.cursor()
        
        # Check verification code
        cursor.execute('''
            SELECT id, created_at FROM email_verifications 
            WHERE email_hash = ? AND verification_code = ?
        ''', (email_hash, verification_code))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({"error": "Invalid verification code"}), 400
        
        # Check if code is expired (10 minutes)
        created_at = datetime.fromisoformat(result[1])
        if datetime.now() - created_at > timedelta(minutes=10):
            conn.close()
            return jsonify({"error": "Verification code expired"}), 400
        
        # Mark as verified
        cursor.execute('''
            UPDATE email_verifications 
            SET verified = TRUE 
            WHERE email_hash = ?
        ''', (email_hash,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Email verified successfully: {email}")
        
        return jsonify({
            "message": "Email verified successfully",
            "is_admin": False
        })
        
    except Exception as e:
        logger.error(f"❌ Email verification error: {str(e)}")
        return jsonify({"error": "Verification failed"}), 500

@app.route('/api/analyze-quote', methods=['POST'])
def analyze_quote():
    """Analyze solar quote with enhanced validation"""
    try:
        data = request.get_json()
        logger.info(f"📊 Received analysis request: {data}")
        
        # Extract and validate data with safe conversion
        system_size = safe_float_convert(data.get('system_size'))
        total_price = safe_float_convert(data.get('total_price'))
        has_battery = data.get('has_battery', False)
        battery_brand = data.get('battery_brand', '')
        battery_quantity = safe_int_convert(data.get('battery_quantity'), 1)
        battery_capacity = safe_float_convert(data.get('battery_capacity'))
        user_email = data.get('user_email', '').strip().lower()
        
        # Validation
        if system_size <= 0:
            return jsonify({"error": "System size must be greater than 0"}), 400
        
        if total_price <= 0:
            return jsonify({"error": "Total price must be greater than 0"}), 400
        
        # Check if admin
        is_admin = is_admin_email(user_email)
        analysis_count = 0
        
        if not is_admin and user_email:
            # Check analysis limits for regular users
            email_hash = hash_email(user_email)
            
            conn = sqlite3.connect('email_verification.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT verified, analysis_count FROM email_verifications 
                WHERE email_hash = ?
            ''', (email_hash,))
            
            result = cursor.fetchone()
            
            if result:
                verified, current_count = result
                analysis_count = current_count + 1
                
                # Update analysis count
                cursor.execute('''
                    UPDATE email_verifications 
                    SET analysis_count = ? 
                    WHERE email_hash = ?
                ''', (analysis_count, email_hash))
                
                conn.commit()
            else:
                analysis_count = 1
            
            conn.close()
        
        # Calculate price per kW
        price_per_kw = total_price / system_size if system_size > 0 else 0
        
        # Enhanced grading logic
        grade = "C"
        verdict = "Standard pricing"
        
        # Solar panel pricing analysis (£800-£1200 per kW is fair)
        if price_per_kw < 800:
            grade = "A+"
            verdict = "Excellent value - very competitive pricing"
        elif price_per_kw < 1000:
            grade = "A"
            verdict = "Good value - fair pricing"
        elif price_per_kw < 1200:
            grade = "B"
            verdict = "Reasonable pricing"
        elif price_per_kw < 1500:
            grade = "C"
            verdict = "Average pricing - room for negotiation"
        else:
            grade = "D"
            verdict = "Expensive - consider getting more quotes"
        
        # Battery analysis if included
        if has_battery and battery_brand:
            # Find battery capacity from brand
            if battery_capacity == 0:
                for battery in BATTERY_OPTIONS:
                    if battery["brand"] == battery_brand:
                        battery_capacity = battery["capacity"]
                        break
            
            total_capacity = battery_capacity * battery_quantity
            
            # Adjust verdict for battery pricing
            if "Tesla Powerwall 3" in battery_brand:
                if total_price < 15000:  # Good deal for Tesla + solar
                    verdict += " with excellent battery value"
                elif total_price < 20000:
                    verdict += " with fair battery pricing"
                else:
                    verdict += " but battery seems expensive"
        
        logger.info(f"✅ Analysis completed - Grade: {grade}, User: {user_email}, Admin: {is_admin}")
        
        return jsonify({
            "grade": grade,
            "verdict": verdict,
            "price_per_kw": f"{price_per_kw:.0f}",
            "analysis_count": analysis_count,
            "is_admin": is_admin,
            "system_details": {
                "system_size": f"{system_size}kW",
                "total_price": f"£{total_price:,.0f}",
                "has_battery": has_battery,
                "battery_info": battery_brand if has_battery else "No battery",
                "total_capacity": f"{battery_capacity * battery_quantity} kWh" if has_battery else "N/A"
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Analysis error: {str(e)}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
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

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=False)
