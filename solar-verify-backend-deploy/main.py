from flask import Flask, request, jsonify
from flask_cors import CORS
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
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('solar_verify.db')
    cursor = conn.cursor()
    
    # Users table with GDPR compliance fields
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
    
    # GDPR requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gdpr_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_hash TEXT,
            request_type TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            processed_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Email configuration (you'll need to set these environment variables)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'hello@solarverify.co.uk')

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
        
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def send_welcome_email_with_guide(email):
    """Send welcome email with PDF guide after verification"""
    try:
        msg = MimeMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = email
        msg['Subject'] = "Welcome to Solar✓erify - Your Protection Guide Inside"
        
        html_body = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to Solar✓erify</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #14B8A6;">Welcome to Solar✓erify!</h1>
                    <p style="color: #666;">Your email has been verified successfully</p>
                </div>
                
                <h2>🎉 You're All Set!</h2>
                
                <p>Congratulations! Your email has been verified and you now have access to:</p>
                
                <div style="background: #f0fdfa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <ul style="margin: 0; padding-left: 20px;">
                        <li>✓ <strong>2 additional free quote analyses</strong> (3 total)</li>
                        <li>✓ <strong>Solar Buyer's Protection Guide</strong> (attached PDF)</li>
                        <li>✓ <strong>20 essential questions</strong> to ask installers</li>
                        <li>✓ <strong>Red flags to avoid</strong> when choosing solar</li>
                        <li>✓ <strong>Warranty checklist</strong> for peace of mind</li>
                    </ul>
                </div>
                
                <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #92400e;">⚠️ Important Solar Scam Alert</h3>
                    <p style="margin-bottom: 0;">Did you know that some UK homeowners are being charged £20,000+ for solar systems worth £8,000? Our guide shows you exactly how to spot these scams and protect yourself.</p>
                </div>
                
                <p><strong>Next Steps:</strong></p>
                <ol>
                    <li>Download and read the attached Solar Buyer's Protection Guide</li>
                    <li>Return to Solar✓erify to analyze more quotes</li>
                    <li>Use our checklist when speaking with installers</li>
                </ol>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://solarquoteanalyzer.netlify.app" style="background: #14B8A6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Analyze Another Quote</a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                
                <div style="text-align: center; color: #666; font-size: 12px;">
                    <p>Solar✓erify - Protecting UK homeowners from solar scams</p>
                    <p>Contact us: hello@solarverify.co.uk</p>
                    <p><a href="mailto:hello@solarverify.co.uk?subject=Unsubscribe">Unsubscribe</a> | <a href="mailto:hello@solarverify.co.uk?subject=Data%20Request">Data Requests</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MimeText(html_body, 'html'))
        
        # Note: In production, you would attach the actual PDF guide here
        # For now, we'll just send the email without attachment
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        return False

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
                last_sent_time = datetime.datetime.fromisoformat(last_sent)
                if (datetime.datetime.now() - last_sent_time).seconds < 3600 and attempts >= 3:
                    return jsonify({'error': 'Too many verification attempts. Please try again later.'}), 429
            
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
            last_sent_time = datetime.datetime.fromisoformat(last_sent)
            if (datetime.datetime.now() - last_sent_time).seconds > 1800:  # 30 minutes
                return jsonify({'error': 'Verification code expired'}), 400
        
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
        
        # Send welcome email with guide
        send_welcome_email_with_guide(email)
        
        logger.info(f"Email verified for {email_hash[:8]}...")
        return jsonify({'message': 'Email verified successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error in verify_email: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification code"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        email_hash = hash_email(email)
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        # Check if user exists and is not verified
        cursor.execute('''
            SELECT id, verification_attempts, last_verification_sent 
            FROM users 
            WHERE email_hash = ? AND is_verified = FALSE
        ''', (email_hash,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found or already verified'}), 404
        
        user_id, attempts, last_sent = user
        
        # Rate limiting
        if last_sent:
            last_sent_time = datetime.datetime.fromisoformat(last_sent)
            if (datetime.datetime.now() - last_sent_time).seconds < 60:  # 1 minute cooldown
                return jsonify({'error': 'Please wait before requesting another code'}), 429
        
        new_code = generate_verification_code()
        current_time = datetime.datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE users 
            SET verification_code = ?, last_verification_sent = ?, verification_attempts = verification_attempts + 1
            WHERE id = ?
        ''', (new_code, current_time, user_id))
        
        conn.commit()
        conn.close()
        
        if send_verification_email(email, new_code):
            return jsonify({'message': 'New verification code sent'}), 200
        else:
            return jsonify({'error': 'Failed to send verification email'}), 500
            
    except Exception as e:
        logger.error(f"Error in resend_verification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/analyze-quote', methods=['POST'])
def analyze_quote():
    """Enhanced quote analysis with improved pricing logic"""
    try:
        data = request.get_json()
        
        # Extract data
        system_size = float(data.get('system_size', 0))
        has_battery = data.get('has_battery', False)
        battery_brand = data.get('battery_brand')
        battery_quantity = int(data.get('battery_quantity', 0))
        battery_size = float(data.get('battery_size', 0))
        total_battery_capacity = float(data.get('total_battery_capacity', 0))
        total_price = float(data.get('total_price', 0))
        
        if system_size <= 0 or total_price <= 0:
            return jsonify({'error': 'Invalid system size or price'}), 400
        
        # Enhanced pricing logic with component-specific calculations
        
        # Base installation cost
        installation_cost = 2000
        
        # Battery pricing by brand (fair market prices)
        battery_prices = {
            'Tesla Powerwall 3': 7750,
            'Tesla Powerwall 2': 7500,
            'Enphase IQ Battery 5P': 4200,
            'Enphase IQ Battery 10': 4800,
            'Enphase IQ Battery 10T': 5000,
            'GivEnergy Giv-Bat 2.6': 3200,
            'GivEnergy Giv-Bat 5.2': 3800,
            'GivEnergy Giv-Bat 9.5': 4500,
            'Fox ESS ECS2900': 3000,
            'Fox ESS ECS4100': 3500,
            'Pylontech Force H2': 4000,
            'Pylontech Force L2': 3200,
            'Solax Triple Power T58': 4100,
            'Solax Triple Power T63': 4300,
            'Huawei LUNA2000-5': 3900,
            'Huawei LUNA2000-10': 4700,
            'LG Chem RESU10H': 4600,
            'LG Chem RESU16H': 6200
        }
        
        # Calculate expected battery cost
        expected_battery_cost = 0
        if has_battery and battery_brand and battery_quantity > 0:
            if battery_brand in battery_prices:
                expected_battery_cost = battery_prices[battery_brand] * battery_quantity
            else:
                # For "Other" batteries, estimate based on capacity
                expected_battery_cost = total_battery_capacity * 400  # £400 per kWh average
        
        # Calculate expected solar panel cost
        expected_solar_cost = system_size * 1000  # £1000 per kW average
        
        # Calculate total expected cost
        expected_total_cost = expected_solar_cost + expected_battery_cost + installation_cost
        
        # Calculate actual solar cost (total price minus battery and installation)
        actual_solar_cost = total_price - expected_battery_cost - installation_cost
        actual_price_per_kw = actual_solar_cost / system_size if system_size > 0 else 0
        
        # Grading logic based on solar panel pricing
        # Fair range for solar panels: £800-£1200 per kW
        if actual_price_per_kw <= 800:
            grade = 'A'
            verdict = "Excellent value for solar panels"
        elif actual_price_per_kw <= 1000:
            grade = 'B'
            verdict = "Good value for solar panels"
        elif actual_price_per_kw <= 1200:
            grade = 'C'
            verdict = "Fair pricing for solar panels"
        elif actual_price_per_kw <= 1500:
            grade = 'D'
            verdict = "Above average pricing for solar panels"
        else:
            grade = 'F'
            verdict = "Overpriced solar panels"
        
        # Adjust verdict if battery is included
        if has_battery:
            battery_value_ratio = expected_battery_cost / (battery_quantity * battery_prices.get(battery_brand, total_battery_capacity * 400))
            if battery_value_ratio >= 0.9:
                verdict += ". Good battery pricing."
            elif battery_value_ratio >= 0.7:
                verdict += ". Fair battery pricing."
            else:
                verdict += ". Excellent battery value."
        
        # Log the analysis (with privacy protection)
        user_email_hash = None  # We don't track individual analyses to specific users for privacy
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO analysis_logs (user_email_hash, system_size, has_battery, battery_brand, 
                                     battery_quantity, total_price, grade, verdict)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_email_hash, system_size, has_battery, battery_brand, 
              battery_quantity, total_price, grade, verdict))
        conn.commit()
        conn.close()
        
        # Prepare response (simplified for free version)
        response = {
            'system_size': system_size,
            'has_battery': has_battery,
            'battery_brand': battery_brand,
            'battery_quantity': battery_quantity,
            'total_battery_capacity': total_battery_capacity,
            'total_price': total_price,
            'price_per_kw': round(actual_price_per_kw, 0),
            'grade': grade,
            'verdict': verdict
        }
        
        logger.info(f"Quote analyzed: {system_size}kW, £{total_price}, Grade: {grade}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in analyze_quote: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500

@app.route('/api/gdpr-request', methods=['POST'])
def gdpr_request():
    """Handle GDPR data requests"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        request_type = data.get('request_type')  # 'access', 'delete', 'portability'
        
        if not email or not request_type:
            return jsonify({'error': 'Email and request type required'}), 400
        
        if request_type not in ['access', 'delete', 'portability']:
            return jsonify({'error': 'Invalid request type'}), 400
        
        email_hash = hash_email(email)
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        # Log the GDPR request
        cursor.execute('''
            INSERT INTO gdpr_requests (email_hash, request_type)
            VALUES (?, ?)
        ''', (email_hash, request_type))
        
        conn.commit()
        conn.close()
        
        # In production, this would trigger an automated process or notify administrators
        logger.info(f"GDPR {request_type} request received for {email_hash[:8]}...")
        
        return jsonify({
            'message': f'Your {request_type} request has been received. We will process it within 30 days and contact you at {email}.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in gdpr_request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/unsubscribe', methods=['POST'])
def unsubscribe():
    """Handle unsubscribe requests"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        email_hash = hash_email(email)
        
        conn = sqlite3.connect('solar_verify.db')
        cursor = conn.cursor()
        
        # Mark user as unsubscribed (delete their record for privacy)
        cursor.execute('DELETE FROM users WHERE email_hash = ?', (email_hash,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"User unsubscribed: {email_hash[:8]}...")
        return jsonify({'message': 'You have been successfully unsubscribed'}), 200
        
    except Exception as e:
        logger.error(f"Error in unsubscribe: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'version': '2.0.0-gdpr-compliant'
    }), 200

if __name__ == '__main__':
    # Set up email configuration reminder
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("Email configuration not set. Email verification will not work.")
        logger.warning("Set SMTP_USERNAME and SMTP_PASSWORD environment variables.")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

