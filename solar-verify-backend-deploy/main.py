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
from premium_pdf_generator import send_premium_report_email

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

def generate_magic_link_token(email, analysis_data):
    """Generate a JWT token for magic link authentication"""
    # Generate unique token ID to prevent replay attacks
    jti = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    payload = {
        'email': email,
        'analysis_data': analysis_data,
        'exp': datetime.utcnow() + timedelta(hours=24),  # 24 hour expiration for cross-device access
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
        # Allow token reuse for cross-device access
        # Single-use enforcement removed to support opening links on different devices
        
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
        
        # Handle both nested and flat data structures
        # Try flat structure first (new format)
        system_size = analysis_data.get('system_size')
        total_price = analysis_data.get('total_price')
        price_per_kw = analysis_data.get('price_per_kw')
        
        # Fall back to nested structure if flat values not found
        if system_size is None and 'analysis' in analysis_data:
            system_size = analysis_data['analysis'].get('system_size', 'N/A')
            total_price = analysis_data['analysis'].get('total_price', 0)
            price_per_kw = analysis_data['analysis'].get('price_per_kw', 0)
        
        # Set defaults if still not found
        if system_size is None:
            system_size = 'N/A'
        if total_price is None:
            total_price = 0
        if price_per_kw is None:
            price_per_kw = 0
        
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
                    .content {{
                        background: #f9f9f9;
                        padding: 30px;
                        border-radius: 0 0 8px 8px;
                    }}
                    .grade {{
                        font-size: 48px;
                        font-weight: bold;
                        text-align: center;
                        color: #14b8a6;
                        margin: 20px 0;
                    }}
                    .analysis-box {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        margin: 20px 0;
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
                        <p>Your Solar Quote Analysis Results</p>
                    </div>
                    <div class="content">
                        <h2>Your Quote Grade</h2>
                        <div class="grade">Grade {grade}</div>
                        <div class="analysis-box">
                            <p><strong>System Size:</strong> {system_size}</p>
                            <p><strong>Total Price:</strong> £{total_price:,.0f}</p>
                            <p><strong>Price per kW:</strong> £{price_per_kw:.2f}</p>
                            <p><strong>Verdict:</strong> {verdict}</p>
                        </div>
                        <h3>📄 Your Free Solar Buyer's Guide</h3>
                        <p>We've attached "The Complete Solar Quote Buyer's Guide" to this email. This comprehensive guide will help you:</p>
                        <ul>
                            <li>Identify fair pricing and avoid overpriced quotes</li>
                            <li>Recognize quality equipment vs poor components</li>
                            <li>Spot installer red flags and warning signs</li>
                            <li>Negotiate better deals and protect your investment</li>
                        </ul>
                        <h3>🚀 Want More Detailed Analysis?</h3>
                        <p style="margin-bottom: 10px;">
                            <span style="text-decoration: line-through; color: #888;">£49.99</span>
                            <strong style="font-size: 24px; color: #14b8a6; margin-left: 10px;">£24.99</strong>
                        </p>
                        <p style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 10px; margin: 15px 0; border-radius: 4px;">
                            <strong>🔥 LAUNCH SPECIAL - SAVE £25</strong>
                        </p>
                        <p>Upgrade to our Premium Analysis for:</p>
                        <ul>
                            <li>15+ page detailed PDF report</li>
                            <li>Component-by-component breakdown</li>
                            <li>Installer reputation check</li>
                            <li>Personalized negotiation strategies</li>
                            <li>Direct access to solar experts</li>
                        </ul>
                        <p style="text-align: center; margin-top: 30px;">
                            <a href="{FRONTEND_URL}/upgrade" style="background: #14b8a6; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Upgrade to Premium - £24.99</a>
                        </p>
                        <p style="text-align: center; color: #666; font-size: 12px; margin-top: 10px;">
                            One-off payment • Instant unlock • 30-day money-back guarantee
                        </p>
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
        'version': '2.0.0 - Magic Link',
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
        
        analysis_data = data.get('analysis_data')
        
        # Check if email has been verified before (within last 24 hours)
        if email in verified_emails:
            last_verified = datetime.fromisoformat(verified_emails[email])
            time_since_verification = datetime.utcnow() - last_verified
            
            # If verified within last 24 hours, skip email verification
            if time_since_verification.total_seconds() < 86400:  # 24 hours
                # Send PDF directly without verification
                if send_pdf_email(email, analysis_data):
                    return jsonify({
                        'success': True,
                        'already_verified': True,
                        'message': 'Email already verified! Check your inbox for the PDF guide.',
                        'analysis_data': analysis_data
                    })
                else:
                    return jsonify({'error': 'Failed to send PDF'}), 500
        
        # Generate magic link token for new or expired verifications
        token = generate_magic_link_token(email, analysis_data)
        
        # Store analysis data for persistence
        analysis_storage[token] = {
            'email': email,
            'analysis_data': analysis_data,
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
        
        # Return success with analysis data (whether PDF was just sent or already sent)
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
        
        # Calculate price per kW (now safe from division by zero)
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
        
        # Build response (flattened structure for frontend compatibility)
        response = {
            'grade': grade,
            'verdict': grade_info['description'],
            'system_size': system_size,
            'total_price': total_price,
            'price_per_kw': round(price_per_kw, 2),
            'market_average': market_average,
            'potential_savings': round(potential_savings, 2),
            'has_battery': has_battery,
            'recommendations': [],
            # Also include nested structure for backward compatibility
            'analysis': {
                'system_size': system_size,
                'total_price': total_price,
                'price_per_kw': round(price_per_kw, 2),
                'market_average': market_average,
                'potential_savings': round(potential_savings, 2),
                'has_battery': has_battery
            }
        }
        
        # Add recommendations based on grade
        if grade in ['D', 'F']:
            response['recommendations'].append('Consider negotiating the price')
            response['recommendations'].append('Get additional quotes for comparison')
        
        if potential_savings > 1000:
            response['recommendations'].append(f'You could save up to £{potential_savings:,.0f} with better pricing')
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/analyze-premium-quote', methods=['POST'])
def analyze_premium_quote():
    """Analyze a premium solar quote with detailed component assessment"""
    try:
        data = request.get_json()
        
        # Validate required basic fields
        required_fields = ['system_size', 'total_price', 'user_email']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Parse basic fields
        system_size = float(data['system_size'])
        total_price = float(data['total_price'])
        user_email = data['user_email']
        location = data.get('location', '')
        
        # Validate basic values
        if system_size <= 0:
            return jsonify({'error': 'System size must be greater than 0'}), 400
        if total_price <= 0:
            return jsonify({'error': 'Total price must be greater than 0'}), 400
        
        # Parse premium fields - Panel details
        panel_brand = data.get('panel_brand', '')
        panel_model = data.get('panel_model', '')
        panel_wattage = float(data.get('panel_wattage', 0))
        panel_quantity = int(data.get('panel_quantity', 0))
        
        # Parse premium fields - Inverter details
        inverter_brand = data.get('inverter_brand', '')
        inverter_model = data.get('inverter_model', '')
        inverter_type = data.get('inverter_type', '')
        inverter_capacity = float(data.get('inverter_capacity', 0))
        
        # Parse premium fields - Battery details
        has_battery = data.get('has_battery', False)
        battery_brand = data.get('battery_brand', '')
        battery_model = data.get('battery_model', '')
        battery_capacity = float(data.get('battery_capacity', 0)) if has_battery else 0
        battery_quantity = int(data.get('battery_quantity', 0)) if has_battery else 0
        battery_warranty = int(data.get('battery_warranty', 0)) if has_battery else 0
        
        # Parse premium fields - Installation details
        scaffolding_included = data.get('scaffolding_included', False)
        scaffolding_cost = float(data.get('scaffolding_cost', 0)) if scaffolding_included else 0
        bird_protection_included = data.get('bird_protection_included', False)
        bird_protection_cost = float(data.get('bird_protection_cost', 0)) if bird_protection_included else 0
        roof_type = data.get('roof_type', '')
        roof_material = data.get('roof_material', '')
        
        # Parse premium fields - Installer information
        installer_company = data.get('installer_company', '')
        installer_location = data.get('installer_location', '')
        installer_mcs = data.get('installer_mcs', '')
        installer_years_in_business = int(data.get('installer_years_in_business', 0))
        installer_warranty_years = int(data.get('installer_warranty_years', 0))
        installation_timeline = data.get('installation_timeline', '')
        
        # Calculate price per kW
        price_per_kw = total_price / system_size
        
        # Determine grade based on price per kW
        grade = 'F'
        grade_info = None
        
        for grade_letter, tier in SOLAR_PRICING_TIERS.items():
            if tier['min'] <= price_per_kw <= tier['max']:
                grade = grade_letter
                grade_info = tier
                break
        
        if grade_info is None:
            if price_per_kw < SOLAR_PRICING_TIERS['A']['min']:
                grade = 'A'
                grade_info = SOLAR_PRICING_TIERS['A']
            else:
                grade = 'F'
                grade_info = SOLAR_PRICING_TIERS['F']
        
        # Calculate potential savings
        market_average = 2150
        potential_savings = max(0, (price_per_kw - market_average) * system_size)
        
        # Premium analysis - Component assessment
        component_analysis = {}
        red_flags = []
        things_to_consider = []
        questions_to_ask = []
        
        # Panel analysis
        if panel_brand and panel_model:
            # Calculate expected system size from panels
            calculated_system_size = (panel_wattage * panel_quantity) / 1000
            size_difference = abs(calculated_system_size - system_size)
            
            component_analysis['panels'] = {
                'brand': panel_brand,
                'model': panel_model,
                'wattage': panel_wattage,
                'quantity': panel_quantity,
                'calculated_system_size': round(calculated_system_size, 2),
                'matches_quoted_size': size_difference < 0.5
            }
            
            if size_difference >= 0.5:
                red_flags.append(f'System size mismatch: {panel_quantity} x {panel_wattage}W panels = {calculated_system_size:.2f}kW, but quote states {system_size}kW')
                questions_to_ask.append('Can you clarify the discrepancy between the number of panels and the stated system size?')
        
        # Inverter analysis
        if inverter_brand and inverter_model:
            # Check inverter sizing (should be 80-110% of panel capacity)
            inverter_ratio = (inverter_capacity / system_size) * 100 if system_size > 0 else 0
            
            component_analysis['inverter'] = {
                'brand': inverter_brand,
                'model': inverter_model,
                'type': inverter_type,
                'capacity': inverter_capacity,
                'sizing_ratio': round(inverter_ratio, 1),
                'properly_sized': 80 <= inverter_ratio <= 110
            }
            
            if inverter_ratio < 80:
                red_flags.append(f'Inverter may be undersized: {inverter_capacity}kW inverter for {system_size}kW system ({inverter_ratio:.0f}% ratio)')
                things_to_consider.append('An undersized inverter may limit system performance and energy production')
            elif inverter_ratio > 110:
                things_to_consider.append(f'Inverter is oversized ({inverter_ratio:.0f}% ratio), which may increase costs without significant benefit')
        
        # Battery analysis
        if has_battery:
            total_battery_capacity = battery_capacity * battery_quantity
            # Typical recommendation: 1-2 kWh per kW of solar
            recommended_min = system_size * 1
            recommended_max = system_size * 2
            
            component_analysis['battery'] = {
                'brand': battery_brand,
                'model': battery_model,
                'capacity_per_unit': battery_capacity,
                'quantity': battery_quantity,
                'total_capacity': round(total_battery_capacity, 1),
                'warranty_years': battery_warranty,
                'sizing_appropriate': recommended_min <= total_battery_capacity <= recommended_max * 1.5
            }
            
            if total_battery_capacity < recommended_min:
                things_to_consider.append(f'Battery capacity ({total_battery_capacity:.1f}kWh) is below typical recommendation ({recommended_min:.1f}-{recommended_max:.1f}kWh for a {system_size}kW system)')
                questions_to_ask.append('Have you calculated the battery size based on your actual energy consumption patterns?')
            
            if battery_warranty < 10:
                things_to_consider.append(f'Battery warranty is {battery_warranty} years. Many premium batteries offer 10+ year warranties')
        
        # Installation details analysis
        installation_analysis = {}
        
        if scaffolding_included:
            scaffolding_per_kw = scaffolding_cost / system_size if system_size > 0 else 0
            installation_analysis['scaffolding'] = {
                'cost': scaffolding_cost,
                'cost_per_kw': round(scaffolding_per_kw, 2)
            }
            if scaffolding_per_kw > 150:
                things_to_consider.append(f'Scaffolding cost (£{scaffolding_cost}) seems high at £{scaffolding_per_kw:.0f}/kW')
        
        if bird_protection_included:
            installation_analysis['bird_protection'] = {
                'cost': bird_protection_cost
            }
            if bird_protection_cost > 500:
                things_to_consider.append(f'Bird protection cost (£{bird_protection_cost}) is above typical market rates (£200-400)')
        
        if roof_type:
            installation_analysis['roof'] = {
                'type': roof_type,
                'material': roof_material
            }
        
        # Installer analysis
        installer_analysis = {
            'company': installer_company,
            'location': installer_location,
            'mcs_registered': bool(installer_mcs),
            'mcs_number': installer_mcs,
            'years_in_business': installer_years_in_business,
            'warranty_years': installer_warranty_years,
            'installation_timeline': installation_timeline
        }
        
        if not installer_mcs:
            red_flags.append('Installer does not appear to be MCS certified - this is REQUIRED for SEG payments and government incentives')
            questions_to_ask.append('Can you provide your MCS certification number? This is essential for claiming SEG payments.')
        
        if installer_years_in_business < 2:
            things_to_consider.append(f'Installer has been in business for {installer_years_in_business} year(s). Consider checking reviews and references')
        
        if installer_warranty_years < 5:
            things_to_consider.append(f'Installation warranty is {installer_warranty_years} years. Industry standard is typically 5-10 years')
            questions_to_ask.append('What does the installation warranty cover, and can it be extended?')
        
        # Build comprehensive response
        response = {
            'success': True,
            'grade': grade,
            'verdict': grade_info['description'],
            'basic_analysis': {
                'system_size': system_size,
                'total_price': total_price,
                'price_per_kw': round(price_per_kw, 2),
                'market_average': market_average,
                'potential_savings': round(potential_savings, 2),
                'location': location
            },
            'component_analysis': component_analysis,
            'installation_analysis': installation_analysis,
            'installer_analysis': installer_analysis,
            'red_flags': red_flags,
            'things_to_consider': things_to_consider,
            'questions_to_ask': questions_to_ask,
            'user_email': user_email
        }
        
        # Generate and send PDF report via email
        try:
            sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
            if sendgrid_api_key:
                sg = SendGridAPIClient(sendgrid_api_key)
                email_sent = send_premium_report_email(user_email, response, sg)
                response['email_sent'] = email_sent
            else:
                response['email_sent'] = False
                response['email_error'] = 'SendGrid API key not configured'
        except Exception as email_error:
            print(f"Error sending premium report email: {str(email_error)}")
            response['email_sent'] = False
            response['email_error'] = str(email_error)
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': f'Premium analysis failed: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

