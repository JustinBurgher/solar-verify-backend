from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import random
import string
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import sqlite3
import hashlib
import datetime
import os
import re

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'hello@solarverify.co.uk')

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
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")

# Initialize database
init_db()

# Battery database with accurate specifications and pricing
BATTERY_DATABASE = {
    'tesla_powerwall_3': {
        'name': 'Tesla Powerwall 3',
        'capacity': 13.5,
        'fair_price_min': 7500,
        'fair_price_max': 8000
    },
    'tesla_powerwall_2': {
        'name': 'Tesla Powerwall 2',
        'capacity': 13.5,
        'fair_price_min': 6500,
        'fair_price_max': 7500
    },
    'enphase_iq_battery_5p': {
        'name': 'Enphase IQ Battery 5P',
        'capacity': 5.0,
        'fair_price_min': 4000,
        'fair_price_max': 5000
    },
    'enphase_iq_battery_10': {
        'name': 'Enphase IQ Battery 10',
        'capacity': 10.1,
        'fair_price_min': 6000,
        'fair_price_max': 7000
    },
    'givenergy_giv_bat_9_5': {
        'name': 'GivEnergy Giv-Bat 9.5',
        'capacity': 9.5,
        'fair_price_min': 3000,
        'fair_price_max': 4000
    },
    'givenergy_giv_bat_13_5': {
        'name': 'GivEnergy Giv-Bat 13.5',
        'capacity': 13.5,
        'fair_price_min': 4000,
        'fair_price_max': 5000
    },
    'pylontech_us3000c': {
        'name': 'Pylontech US3000C',
        'capacity': 3.55,
        'fair_price_min': 1500,
        'fair_price_max': 2000
    },
    'pylontech_us5000': {
        'name': 'Pylontech US5000',
        'capacity': 4.8,
        'fair_price_min': 2000,
        'fair_price_max': 2500
    },
    'solax_triple_power_t58': {
        'name': 'Solax Triple Power T58',
        'capacity': 5.8,
        'fair_price_min': 2500,
        'fair_price_max': 3500
    },
    'solax_triple_power_t63': {
        'name': 'Solax Triple Power T63',
        'capacity': 6.3,
        'fair_price_min': 3000,
        'fair_price_max': 4000
    },
    'lg_resu_10h': {
        'name': 'LG RESU 10H',
        'capacity': 9.8,
        'fair_price_min': 4500,
        'fair_price_max': 5500
    },
    'lg_resu_16h': {
        'name': 'LG RESU 16H',
        'capacity': 16.0,
        'fair_price_min': 6500,
        'fair_price_max': 7500
    },
    'byd_battery_box_premium_hv': {
        'name': 'BYD Battery-Box Premium HV',
        'capacity': 11.04,
        'fair_price_min': 4000,
        'fair_price_max': 5000
    },
    'alpha_ess_smile_b3': {
        'name': 'Alpha ESS SMILE-B3',
        'capacity': 10.1,
        'fair_price_min': 3500,
        'fair_price_max': 4500
    },
    'solarwatt_myreserve_matrix': {
        'name': 'SOLARWATT MyReserve Matrix',
        'capacity': 9.6,
        'fair_price_min': 5000,
        'fair_price_max': 6000
    },
    'sonnen_sonnencore': {
        'name': 'sonnen sonnenCore',
        'capacity': 10.0,
        'fair_price_min': 6000,
        'fair_price_max': 7000
    },
    'huawei_luna2000': {
        'name': 'Huawei LUNA2000',
        'capacity': 5.0,
        'fair_price_min': 2500,
        'fair_price_max': 3500
    },
    'fronius_solar_battery': {
        'name': 'Fronius Solar Battery',
        'capacity': 4.5,
        'fair_price_min': 2500,
        'fair_price_max': 3500
    },
    'other': {
        'name': 'Other Battery',
        'capacity': 0,  # User will specify
        'fair_price_min': 2000,
        'fair_price_max': 8000
    }
}

def hash_email(email):
    """Create a hash of the email for privacy protection"""
    return hashlib.sha256(email.lower().encode()).hexdigest()

def is_valid_email(email):
    """Enhanced email validation"""
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(pattern, email):
        return False
    
    # Block common fake domains
    fake_domains = ['test.com', 'example.com', 'fake.com', 'temp.com', '123.com', 'tempmail.com']
    domain = email.split('@')[1].lower()
    
    return domain not in fake_domains

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, code):
    """Send verification email with GDPR-compliant content"""
    try:
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured")
            return False
            
        msg = MimeMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = email
        msg['Subject'] = "Solar✓erify - Verify Your Email Address"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Verify Your Email - Solar✓erify</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #14B8A6;">Solar✓erify</h1>
                    <p style="color: #666;">Protecting UK homeowners from solar scams</p>
                </div>
                
                <h2>Verify Your Email Address</h2>
                
                <p>Thank you for choosing Solar✓erify! To unlock your additional free analyses and receive your Solar Buyer's Protection Guide, please verify your email address.</p>
                
                <div style="background: #f0fdfa; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <h3 style="margin: 0; color: #14B8A6;">Your Verification Code</h3>
                    <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #0f766e; margin: 10px 0;">
                        {code}
                    </div>
                    <p style="margin: 0; color: #666; font-size: 14px;">Enter this code on the Solar✓erify website</p>
                </div>
                
                <p><strong>What you'll get after verification:</strong></p>
                <ul>
                    <li>✓ 2 additional free quote analyses</li>
                    <li>✓ Solar Buyer's Protection Guide (PDF)</li>
                    <li>✓ 20 essential questions to ask installers</li>
                    <li>✓ Red flags to avoid</li>
                    <li>✓ Warranty checklist</li>
                </ul>
                
                <div style="background: #f9fafb; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 12px; color: #666;">
                    <h4 style="margin-top: 0;">Data Protection Notice</h4>
                    <p>This email confirms your consent to receive our Solar Buyer's Protection Guide and occasional solar industry insights. We respect your privacy and will never share your data with third parties. You can unsubscribe at any time by contacting hello@solarverify.co.uk</p>
                </div>
                
                <p>If you didn't request this verification, please ignore this email.</p>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                
                <div style="text-align: center; color: #666; font-size: 12px;">
                    <p>Solar✓erify - Protecting UK homeowners from solar scams</p>
                    <p>Contact us: hello@solarverify.co.uk</p>
                    <p>This email was sent because you requested email verification on our website.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MimeText(html_body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Verification email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def calculate_grade(percentage):
    """Convert percentage to letter grade"""
    if percentage <= 70:
        return 'A'
    elif percentage <= 85:
        return 'B'
    elif percentage <= 100:
        return 'C'
    elif percentage <= 120:
        return 'D'
    else:
        return 'F'

def get_verdict(grade, solar_percentage, battery_percentage=None):
    """Generate verdict based on grades"""
    verdicts = {
        'A': 'Excellent value',
        'B': 'Good value for money', 
        'C': 'Fair market price',
        'D': 'Above market rate',
        'F': 'Severely overpriced'
    }
    
    base_verdict = verdicts.get(grade, 'Unknown')
    
    # Add specific insights
    if battery_percentage:
        if solar_percentage <= 80 and battery_percentage <= 80:
            return f"{base_verdict} - Outstanding deal on both solar and battery!"
        elif solar_percentage <= 80:
            return f"{base_verdict} - Excellent solar pricing, good battery value"
        elif battery_percentage <= 80:
            return f"{base_verdict} - Good solar pricing, excellent battery value"
    
    return base_verdict

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'version': '2.1.0-email-enabled',
        'email_configured': bool(SMTP_USERNAME and SMTP_PASSWORD)
    }), 200

@app.route('/api/analyze-quote', methods=['POST'])
def analyze_quote():
    """Analyze solar quote with enhanced battery support"""
    try:
        data = request.get_json()
        
        # Extract data
        system_size = float(data.get('system_size', 0))
        total_price = float(data.get('total_price', 0))
        has_battery = data.get('has_battery', False)
        battery_brand = data.get('battery_brand', '')
        battery_quantity = int(data.get('battery_quantity', 1))
        battery_capacity = float(data.get('battery_capacity', 0))
        
        if system_size <= 0 or total_price <= 0:
            return jsonify({'error': 'Invalid system size or price'}), 400
        
        # Solar panel pricing (fair range: £800-£1,200 per kW)
        solar_fair_min = system_size * 800
        solar_fair_max = system_size * 1200
        
        # Installation cost estimate
        installation_cost = 2000  # Base installation cost
        
        # Calculate battery costs
        battery_cost = 0
        total_battery_capacity = 0
        
        if has_battery and battery_brand in BATTERY_DATABASE:
            battery_info = BATTERY_DATABASE[battery_brand]
            
            if battery_brand == 'other' and battery_capacity > 0:
                # User specified custom battery capacity
                total_battery_capacity = battery_capacity * battery_quantity
                # Estimate cost based on capacity (£400-600 per kWh)
                battery_cost = battery_capacity * battery_quantity * 500
            else:
                # Use database values
                total_battery_capacity = battery_info['capacity'] * battery_quantity
                battery_cost = ((battery_info['fair_price_min'] + battery_info['fair_price_max']) / 2) * battery_quantity
        
        # Calculate solar cost (total - battery - installation)
        solar_cost = total_price - battery_cost - installation_cost
        
        # Ensure solar cost is not negative
        if solar_cost < 0:
            solar_cost = total_price * 0.6  # Assume 60% for solar if calculation goes negative
        
        # Calculate price per kW for solar only
        price_per_kw = solar_cost / system_size
        
        # Calculate solar percentage of fair price
        solar_fair_average = (solar_fair_min + solar_fair_max) / 2
        solar_percentage = (solar_cost / solar_fair_average) * 100
        
        # Calculate battery percentage if applicable
        battery_percentage = None
        if has_battery and battery_cost > 0:
            battery_info = BATTERY_DATABASE.get(battery_brand, {})
            if battery_brand != 'other' and 'fair_price_min' in battery_info:
                battery_fair_average = ((battery_info['fair_price_min'] + battery_info['fair_price_max']) / 2) * battery_quantity
                battery_percentage = (battery_cost / battery_fair_average) * 100
        
        # Overall grade based on weighted average
        if battery_percentage:
            # Weight solar and battery equally
            overall_percentage = (solar_percentage + battery_percentage) / 2
        else:
            overall_percentage = solar_percentage
        
        grade = calculate_grade(overall_percentage)
        verdict = get_verdict(grade, solar_percentage, battery_percentage)
        
        # Prepare response (Option A: Hidden detailed breakdown)
        response = {
            'grade': grade,
            'verdict': verdict,
            'price_per_kw': round(price_per_kw, 0),
            'system_details': {
                'system_size': system_size,
                'total_price': total_price,
                'has_battery': has_battery
            }
        }
        
        # Add battery details if applicable
        if has_battery:
            response['system_details']['battery_info'] = {
                'brand': BATTERY_DATABASE.get(battery_brand, {}).get('name', battery_brand),
                'quantity': battery_quantity,
                'total_capacity': round(total_battery_capacity, 1)
            }
        
        logger.info(f"Quote analyzed: {system_size}kW, £{total_price}, Grade: {grade}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error analyzing quote: {str(e)}")
        return jsonify({'error': 'Failed to analyze quote'}), 500

@app.route('/api/battery-options', methods=['GET'])
def get_battery_options():
    """Get available battery options"""
    try:
        options = []
        for key, battery in BATTERY_DATABASE.items():
            options.append({
                'value': key,
                'label': battery['name'],
                'capacity': battery['capacity']
            })
        
        return jsonify({'battery_options': options}), 200
        
    except Exception as e:
        logger.error(f"Error getting battery options: {str(e)}")
        return jsonify({'error': 'Failed to get battery options'}), 500

@app.route('/api/send-verification', methods=['POST'])
def send_verification():
    """Send verification email with GDPR compliance"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        gdpr_consent = data.get('gdpr_consent', False)
        consent_timestamp = data.get('consent_timestamp')
        
        if not email or not is_valid_email(email):
            return jsonify({'error': 'Invalid email address'}), 400
        
        if not gdpr_consent:
            return jsonify({'error': 'GDPR consent required'}), 400
        
        email_hash = hash_email(email)
        verification_code = generate_verification_code()
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id, verification_attempts, last_verification_sent FROM users WHERE email_hash = ?', (email_hash,))
        user = cursor.fetchone()
        
        current_time = datetime.datetime.now().isoformat()
        
        if user:
            user_id, attempts, last_sent = user
            
            # Rate limiting: max 3 attempts per hour
            if last_sent:
                try:
                    last_sent_time = datetime.datetime.fromisoformat(last_sent)
                    if (datetime.datetime.now() - last_sent_time).seconds < 3600 and attempts >= 3:
                        return jsonify({'error': 'Too many verification attempts. Please try again later.'}), 429
                except:
                    pass  # Continue if timestamp parsing fails
            
            # Update existing user
            cursor.execute('''
                UPDATE users 
                SET verification_code = ?, last_verification_sent = ?, verification_attempts = verification_attempts + 1,
                    gdpr_consent = ?, consent_timestamp = ?
                WHERE email_hash = ?
            ''', (verification_code, current_time, gdpr_consent, consent_timestamp, email_hash))
        else:
            # Create new user
            cursor.execute('''
                INSERT INTO users (email, email_hash, verification_code, last_verification_sent, 
                                 verification_attempts, gdpr_consent, consent_timestamp)
                VALUES (?, ?, ?, ?, 1, ?, ?)
            ''', (email, email_hash, verification_code, current_time, gdpr_consent, consent_timestamp))
        
        conn.commit()
        conn.close()
        
        # Send verification email
        if send_verification_email(email, verification_code):
            logger.info(f"Verification email sent to {email_hash[:8]}...")
            return jsonify({'message': 'Verification email sent successfully'}), 200
        else:
            return jsonify({'error': 'Failed to send verification email'}), 500
            
    except Exception as e:
        logger.error(f"Error in send_verification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    """Verify email with code"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        verification_code = data.get('verification_code', '').strip()
        
        if not email or not verification_code:
            return jsonify({'error': 'Email and verification code required'}), 400
        
        email_hash = hash_email(email)
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        # Check verification code
        cursor.execute('''
            SELECT id, verification_code, last_verification_sent 
            FROM users 
            WHERE email_hash = ? AND is_verified = FALSE
        ''', (email_hash,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found or already verified'}), 404
        
        user_id, stored_code, last_sent = user
        
        # Check if code is expired (30 minutes)
        if last_sent:
            try:
                last_sent_time = datetime.datetime.fromisoformat(last_sent)
                if (datetime.datetime.now() - last_sent_time).seconds > 1800:  # 30 minutes
                    return jsonify({'error': 'Verification code expired'}), 400
            except:
                pass  # Continue if timestamp parsing fails
        
        if stored_code != verification_code:
            return jsonify({'error': 'Invalid verification code'}), 400
        
        # Mark as verified
        cursor.execute('''
            UPDATE users 
            SET is_verified = TRUE, verification_code = NULL 
            WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Email verified for {email_hash[:8]}...")
        return jsonify({'message': 'Email verified successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error in verify_email: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/check-email-status', methods=['POST'])
def check_email_status():
    """Check if email is verified and analysis count"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        email_hash = hash_email(email)
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT is_verified, analysis_count 
            FROM users 
            WHERE email_hash = ?
        ''', (email_hash,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            is_verified, analysis_count = user
            return jsonify({
                'is_verified': bool(is_verified),
                'analysis_count': analysis_count,
                'remaining_analyses': max(0, 3 - analysis_count) if is_verified else 0
            }), 200
        else:
            return jsonify({
                'is_verified': False,
                'analysis_count': 0,
                'remaining_analyses': 0
            }), 200
            
    except Exception as e:
        logger.error(f"Error checking email status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

