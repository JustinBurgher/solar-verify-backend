import os
import random
import string
import jwt
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://solarverify.co.uk')

# In-memory storage for used tokens and analysis data (use Redis or database in production)
used_tokens = set()
# Store analysis data by token for persistence
analysis_storage = {}  # token -> {analysis_data, email, timestamp}
# Store verified emails with timestamp (email -> timestamp)
verified_emails = {}  # Tracks emails that have been verified

# UK Solar Market Data (September 2025)
SOLAR_PRICING_TIERS = {
    'A': {'min': 1400, 'max': 1700, 'description': 'Excellent value - well below market average'},
    'B': {'min': 1700, 'max': 2000, 'description': 'Good value - competitive pricing'},
    'C': {'min': 2000, 'max': 2300, 'description': 'Fair value - around market average'},
    'D': {'min': 2300, 'max': 2600, 'description': 'Above average - consider negotiating'},
    'F': {'min': 2600, 'max': 5000, 'description': 'Overpriced - significant savings possible'}
}

BATTERY_BRANDS = {
    'Tesla Powerwall': {'capacity': 13.5, 'efficiency': 0.9},
    'Enphase': {'capacity': 10.1, 'efficiency': 0.89},
    'SolarEdge': {'capacity': 9.7, 'efficiency': 0.94},
    'Pylontech': {'capacity': 7.4, 'efficiency': 0.95},
    'Fox Battery': {'capacity': 13.8, 'efficiency': 0.92},
    'GivEnergy': {'capacity': 9.5, 'efficiency': 0.93},
    'Other': {'capacity': 10.0, 'efficiency': 0.9}  # Default for custom
}

def calculate_analysis(system_size, total_price, has_battery=False, battery_brand='', battery_quantity=0, battery_capacity=0):
    """Calculate grade and analysis details from quote data"""
    # Calculate price per kW
    price_per_kw = total_price / system_size
    
    # Determine grade based on price per kW
    grade = 'F'  # Default to worst grade
    grade_info = None
    
    for grade_letter, tier in SOLAR_PRICING_TIERS.items():
        if tier['min'] <= price_per_kw <= tier['max']:
            grade = grade_letter
            grade_info = tier
            break
    
    if grade_info is None:
        # Handle edge cases
        if price_per_kw < SOLAR_PRICING_TIERS['A']['min']:
            grade = 'A'
            grade_info = SOLAR_PRICING_TIERS['A']
        else:
            grade = 'F'
            grade_info = SOLAR_PRICING_TIERS['F']
    
    # Calculate potential savings
    market_average = 2150  # £/kW market average
    if price_per_kw > market_average:
        potential_savings = (price_per_kw - market_average) * system_size
    else:
        potential_savings = 0
    
    # Build complete analysis
    return {
        'grade': grade,
        'verdict': grade_info['description'],
        'system_size': system_size,
        'total_price': total_price,
        'price_per_kw': round(price_per_kw, 2),
        'market_average': market_average,
        'potential_savings': round(potential_savings, 2),
        'has_battery': has_battery,
        'battery_brand': battery_brand,
        'battery_quantity': battery_quantity,
        'battery_capacity': battery_capacity
    }

def generate_magic_link_token(email, analysis_data):
    """Generate a JWT token for magic link authentication"""
    # Generate unique token ID to prevent replay attacks
    jti = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    payload = {
        'email': email,
        'analysis_data': analysis_data,
        'exp': datetime.utcnow() + timedelta(minutes=10),  # 10 minute expiration
        'iat': datetime.utcnow(),
        'jti': jti  # JWT ID for single-use enforcement
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token

def cleanup_expired_data():
    """Remove expired tokens and analysis data to prevent memory leaks"""
    current_time = datetime.utcnow()
    expired_tokens = []
    
    for token, data in list(analysis_storage.items()):
        try:
            # Try to decode token to check expiration
            jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            # Token has expired, mark for removal
            expired_tokens.append(token)
        except jwt.InvalidTokenError:
            # Invalid token, mark for removal
            expired_tokens.append(token)
    
    # Remove expired tokens from storage
    for token in expired_tokens:
        analysis_storage.pop(token, None)
        used_tokens.discard(token)
    
    return len(expired_tokens)

def verify_magic_link_token(token, mark_as_used=True):
    """Verify and decode JWT token"""
    try:
        # Check if token has already been used for PDF delivery
        if mark_as_used and token in used_tokens:
            return None, 'Token has already been used'
        
        # Decode and verify token
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        # Mark token as used only if requested (for PDF delivery)
        if mark_as_used:
            used_tokens.add(token)
        
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, 'Token has expired'
    except jwt.InvalidTokenError:
        return None, 'Invalid token'

def send_magic_link_email(email, token):
    """Send magic link via SendGrid"""
    try:
        magic_link = f"{FRONTEND_URL}/verify?token={token}"
        
        message = Mail(
            from_email='justinburgher@solarverify.co.uk',
            to_emails=email,
            subject='Verify Your Email - Solar Verify',
            html_content=f'''
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #14b8a6 0%, #3b82f6 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                        border-radius: 8px 8px 0 0;
                    }}
                    .content {{
                        background: #f9f9f9;
                        padding: 30px;
                        border-radius: 0 0 8px 8px;
                    }}
                    .button {{
                        display: inline-block;
                        background: #14b8a6;
                        color: white;
                        padding: 15px 40px;
                        text-decoration: none;
                        border-radius: 5px;
                        font-weight: bold;
                        margin: 20px 0;
                    }}
                    .button:hover {{
                        background: #0d9488;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 20px;
                        color: #888;
                        font-size: 12px;
                    }}
                    .note {{
                        background: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 15px;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Solar✓erify</h1>
                        <p>Verify your email to access your results</p>
                    </div>
                    <div class="content">
                        <h2>Welcome to Solar Verify!</h2>
                        <p>Thank you for using our solar quote analysis service. Click the button below to verify your email and access your free analysis results and Solar Buyer's Guide:</p>
                        
                        <div style="text-align: center;">
                            <a href="{magic_link}" class="button">Verify Email & Get My Results</a>
                        </div>
                        
                        <div class="note">
                            <strong>⏱️ This link expires in 10 minutes</strong><br>
                            For security, this is a one-time link that can only be used once.
                        </div>
                        
                        <p>If the button doesn't work, copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; color: #14b8a6;">{magic_link}</p>
                        
                        <p style="margin-top: 30px; color: #666;">If you didn't request this email, please ignore it.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Solar✓erify Ltd. All rights reserved.</p>
                        <p>Email: justinburgher@solarverify.co.uk | Website: www.solarverify.co.uk</p>
                    </div>
                </div>
            </body>
            </html>
            '''
        )
        
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_pdf_email(email, analysis_data):
    """Send PDF guide via email after verification"""
    try:
        # Read the PDF file
        pdf_path = os.path.join(os.path.dirname(__file__), 'solar_verify_professional_guide_final.pdf')
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        # Encode PDF to base64
        encoded_pdf = base64.b64encode(pdf_data).decode()
        
        # Extract analysis data (now in flat structure with grade and verdict)
        system_size = analysis_data.get('system_size', 0)
        total_price = analysis_data.get('total_price', 0)
        price_per_kw = analysis_data.get('price_per_kw', 0)
        grade = analysis_data.get('grade', 'N/A')
        verdict = analysis_data.get('verdict', 'Analysis complete')
        
        message = Mail(
            from_email='justinburgher@solarverify.co.uk',
            to_emails=email,
            subject='Your Solar Quote Analysis & Free Buyer\'s Guide',
            html_content=f'''
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #14b8a6 0%, #3b82f6 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                        border-radius: 8px 8px 0 0;
                    }}
                    .grade-badge {{
                        display: inline-block;
                        font-size: 48px;
                        font-weight: bold;
                        background: white;
                        color: #14b8a6;
                        width: 80px;
                        height: 80px;
                        line-height: 80px;
                        border-radius: 50%;
                        margin: 20px 0;
                    }}
                    .content {{
                        background: #f9f9f9;
                        padding: 30px;
                    }}
                    .analysis-box {{
                        background: white;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .metric {{
                        display: inline-block;
                        width: 48%;
                        margin: 10px 0;
                    }}
                    .metric-label {{
                        color: #666;
                        font-size: 14px;
                    }}
                    .metric-value {{
                        color: #333;
                        font-size: 24px;
                        font-weight: bold;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 20px;
                        color: #888;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Solar✓erify</h1>
                        <div class="grade-badge">{grade}</div>
                        <h2>{verdict}</h2>
                    </div>
                    <div class="content">
                        <h2>Your Quote Analysis Results</h2>
                        
                        <div class="analysis-box">
                            <div class="metric">
                                <div class="metric-label">System Size</div>
                                <div class="metric-value">{system_size} kW</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Total Price</div>
                                <div class="metric-value">£{total_price:,.0f}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Price per kW</div>
                                <div class="metric-value">£{price_per_kw:,.2f}</div>
                            </div>
                        </div>
                        
                        <h3>📄 Your Free Solar Buyer's Guide</h3>
                        <p>We've attached our comprehensive Solar Buyer's Guide PDF with 7 critical red flags to watch for when reviewing solar quotes.</p>
                        
                        <p><strong>What's inside:</strong></p>
                        <ul>
                            <li>7 Red Flags in Solar Quotes</li>
                            <li>How to spot overpricing</li>
                            <li>Questions to ask installers</li>
                            <li>Industry pricing benchmarks</li>
                            <li>Warranty and guarantee checklist</li>
                        </ul>
                        
                        <p style="margin-top: 30px;">Need help? Reply to this email or visit our website for more information.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Solar✓erify Ltd. All rights reserved.</p>
                        <p>Email: justinburgher@solarverify.co.uk | Website: www.solarverify.co.uk</p>
                    </div>
                </div>
            </body>
            </html>
            '''
        )
        
        # Attach PDF
        attachment = Attachment()
        attachment.file_content = FileContent(encoded_pdf)
        attachment.file_type = FileType('application/pdf')
        attachment.file_name = FileName('Solar_Buyers_Guide.pdf')
        attachment.disposition = Disposition('attachment')
        message.attachment = attachment
        
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"Error sending PDF email: {str(e)}")
        return False

@app.route('/')
def home():
    """Basic home page"""
    return jsonify({
        'service': 'Solar Verify Analysis API',
        'status': 'operational',
        'version': '2.1.0 - Fixed Analysis Storage',
        'endpoints': {
            'health': '/api/health',
            'analyze': '/api/analyze-quote',
            'send_magic_link': '/api/send-magic-link',
            'verify_token': '/api/verify-token'
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Solar Verify Analysis API',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/send-magic-link', methods=['POST'])
def send_magic_link():
    """Send magic link to user's email"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Get raw analysis data from frontend
        raw_analysis_data = data.get('analysis_data', {})
        
        # Extract values
        system_size = float(raw_analysis_data.get('system_size', 0))
        total_price = float(raw_analysis_data.get('total_price', 0))
        has_battery = raw_analysis_data.get('has_battery', False)
        battery_brand = raw_analysis_data.get('battery_brand', '')
        battery_quantity = int(raw_analysis_data.get('battery_quantity', 0))
        battery_capacity = float(raw_analysis_data.get('battery_capacity', 0))
        
        # Validate
        if system_size <= 0 or total_price <= 0:
            return jsonify({'error': 'Invalid system size or price'}), 400
        
        # Calculate complete analysis with grade and verdict
        complete_analysis = calculate_analysis(
            system_size=system_size,
            total_price=total_price,
            has_battery=has_battery,
            battery_brand=battery_brand,
            battery_quantity=battery_quantity,
            battery_capacity=battery_capacity
        )
        
        # Check if email has been verified before (within last 24 hours)
        if email in verified_emails:
            last_verified = datetime.fromisoformat(verified_emails[email])
            time_since_verification = datetime.utcnow() - last_verified
            
            # If verified within last 24 hours, skip email verification
            if time_since_verification.total_seconds() < 86400:  # 24 hours
                # Send PDF directly without verification
                if send_pdf_email(email, complete_analysis):
                    return jsonify({
                        'success': True,
                        'already_verified': True,
                        'message': 'Email already verified! Check your inbox for the PDF guide.',
                        'analysis_data': complete_analysis
                    })
                else:
                    return jsonify({'error': 'Failed to send PDF'}), 500
        
        # Generate magic link token with COMPLETE analysis (including grade and verdict)
        token = generate_magic_link_token(email, complete_analysis)
        
        # Store complete analysis data for persistence
        analysis_storage[token] = {
            'email': email,
            'analysis_data': complete_analysis,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send email
        if send_magic_link_email(email, token):
            return jsonify({
                'success': True,
                'message': 'Magic link sent successfully. Check your email!'
            })
        else:
            return jsonify({'error': 'Failed to send magic link email'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to send magic link: {str(e)}'}), 500

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    """Verify the magic link token and send PDF"""
    try:
        # Cleanup expired data periodically
        cleanup_expired_data()
        
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Token is required'}), 400
        
        # First verify token without marking as used (to allow retrieval)
        payload, error = verify_magic_link_token(token, mark_as_used=False)
        
        if error:
            return jsonify({'error': error}), 400
        
        # Get stored analysis data
        stored_data = analysis_storage.get(token)
        if not stored_data:
            return jsonify({'error': 'Analysis data not found'}), 404
        
        email = stored_data['email']
        analysis_data = stored_data['analysis_data']
        
        # Check if PDF has already been sent for this token
        if token not in used_tokens:
            # First time verification - send PDF
            if send_pdf_email(email, analysis_data):
                # Mark token as used for PDF delivery
                used_tokens.add(token)
                # Track this email as verified
                verified_emails[email] = datetime.utcnow().isoformat()
            else:
                return jsonify({'error': 'Failed to send PDF'}), 500
        
        # Return success with COMPLETE analysis data (including grade and verdict)
        return jsonify({
            'success': True,
            'message': 'Email verified successfully! Check your email for the PDF guide.',
            'email': email,
            'analysis_data': analysis_data
        })
            
    except Exception as e:
        return jsonify({'error': f'Verification failed: {str(e)}'}), 500

@app.route('/api/analyze-quote', methods=['POST'])
def analyze_quote():
    """Analyze a solar quote and return A-F grade with detailed breakdown"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['system_size', 'total_price']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Parse and validate numeric values
        try:
            system_size = float(data['system_size'])
            total_price = float(data['total_price'])
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid numeric value: {str(e)}'}), 400
        
        # Validate system_size is not zero to prevent division by zero
        if system_size <= 0:
            return jsonify({'error': 'System size must be greater than 0'}), 400
        
        if total_price <= 0:
            return jsonify({'error': 'Total price must be greater than 0'}), 400
        
        has_battery = data.get('has_battery', False)
        battery_brand = data.get('battery_brand', '')
        try:
            battery_quantity = int(data.get('battery_quantity', 0))
            battery_capacity = float(data.get('battery_capacity', 0))
        except (ValueError, TypeError):
            battery_quantity = 0
            battery_capacity = 0
        
        # Use the centralized calculation function
        complete_analysis = calculate_analysis(
            system_size=system_size,
            total_price=total_price,
            has_battery=has_battery,
            battery_brand=battery_brand,
            battery_quantity=battery_quantity,
            battery_capacity=battery_capacity
        )
        
        # Add recommendations based on grade
        recommendations = []
        if complete_analysis['grade'] in ['D', 'F']:
            recommendations.append('Consider negotiating the price')
            recommendations.append('Get additional quotes for comparison')
        
        if complete_analysis['potential_savings'] > 1000:
            recommendations.append(f'You could save up to £{complete_analysis["potential_savings"]:,.0f} with better pricing')
        
        # Build response with nested structure for backwards compatibility
        response = {
            'grade': complete_analysis['grade'],
            'verdict': complete_analysis['verdict'],
            'analysis': {
                'system_size': complete_analysis['system_size'],
                'total_price': complete_analysis['total_price'],
                'price_per_kw': complete_analysis['price_per_kw'],
                'market_average': complete_analysis['market_average'],
                'potential_savings': complete_analysis['potential_savings'],
                'has_battery': complete_analysis['has_battery']
            },
            'recommendations': recommendations
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
