from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///solar_verify.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Enhanced Battery Pricing Database
BATTERY_PRICING = {
    'Tesla Powerwall 3': {'capacity': 13.5, 'fair_price_min': 7500, 'fair_price_max': 8000},
    'Tesla Powerwall 2': {'capacity': 13.5, 'fair_price_min': 7500, 'fair_price_max': 8000},
    'Enphase IQ Battery 5P': {'capacity': 5.0, 'fair_price_min': 4000, 'fair_price_max': 4400},
    'Enphase IQ Battery 10': {'capacity': 10.1, 'fair_price_min': 4600, 'fair_price_max': 5000},
    'Enphase IQ Battery 10T': {'capacity': 10.5, 'fair_price_min': 4800, 'fair_price_max': 5200},
    'GivEnergy Giv-Bat 2.6': {'capacity': 2.6, 'fair_price_min': 3000, 'fair_price_max': 3400},
    'GivEnergy Giv-Bat 5.2': {'capacity': 5.2, 'fair_price_min': 3600, 'fair_price_max': 4000},
    'GivEnergy Giv-Bat 9.5': {'capacity': 9.5, 'fair_price_min': 4300, 'fair_price_max': 4700},
    'Fox ESS ECS2900': {'capacity': 2.9, 'fair_price_min': 2800, 'fair_price_max': 3200},
    'Fox ESS ECS4100': {'capacity': 4.1, 'fair_price_min': 3300, 'fair_price_max': 3700},
    'Pylontech Force H2': {'capacity': 7.1, 'fair_price_min': 3800, 'fair_price_max': 4200},
    'Pylontech Force L2': {'capacity': 3.55, 'fair_price_min': 3000, 'fair_price_max': 3400},
    'Solax Triple Power T58': {'capacity': 5.8, 'fair_price_min': 3900, 'fair_price_max': 4300},
    'Solax Triple Power T63': {'capacity': 6.3, 'fair_price_min': 4100, 'fair_price_max': 4500},
    'Huawei LUNA2000-5': {'capacity': 5.0, 'fair_price_min': 3700, 'fair_price_max': 4100},
    'Huawei LUNA2000-10': {'capacity': 10.0, 'fair_price_min': 4500, 'fair_price_max': 4900},
    'LG Chem RESU10H': {'capacity': 9.8, 'fair_price_min': 4400, 'fair_price_max': 4800},
    'LG Chem RESU16H': {'capacity': 16.0, 'fair_price_min': 6000, 'fair_price_max': 6400},
}

# Solar Panel Pricing (per kW)
SOLAR_PANEL_PRICING = {
    'excellent_max': 1200,    # Grade A: £800-£1200 per kW
    'good_max': 1400,         # Grade B: £1200-£1400 per kW  
    'fair_max': 1600,         # Grade C: £1400-£1600 per kW
    'overpriced_max': 1800,   # Grade D: £1600-£1800 per kW
    # Grade F: Above £1800 per kW
}

# Installation costs (base cost regardless of system size)
BASE_INSTALLATION_COST = 2000  # £2000 base installation cost

# Database Models
class EmailRegistration(db.Model):
    __tablename__ = 'email_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuoteAnalysis(db.Model):
    __tablename__ = 'quote_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    system_size = db.Column(db.Float, nullable=False)
    has_battery = db.Column(db.Boolean, default=False)
    battery_brand = db.Column(db.String(100))
    battery_quantity = db.Column(db.Integer, default=0)
    battery_size = db.Column(db.Float, default=0)
    total_battery_capacity = db.Column(db.Float, default=0)
    total_price = db.Column(db.Float, nullable=False)
    price_per_kw = db.Column(db.Float)
    solar_panel_cost = db.Column(db.Float)
    battery_cost = db.Column(db.Float, default=0)
    installation_cost = db.Column(db.Float)
    grade = db.Column(db.String(1))
    verdict = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def calculate_component_costs(system_size, has_battery, battery_brand, battery_quantity, total_price):
    """
    Enhanced pricing logic that separates solar panels, batteries, and installation costs
    """
    logger.info(f"Calculating costs for: {system_size}kW, Battery: {has_battery}, Brand: {battery_brand}, Qty: {battery_quantity}")
    
    # Base installation cost
    installation_cost = BASE_INSTALLATION_COST
    
    # Calculate battery cost
    battery_cost = 0
    if has_battery and battery_brand and battery_brand in BATTERY_PRICING:
        battery_info = BATTERY_PRICING[battery_brand]
        # Use average of fair price range
        avg_battery_price = (battery_info['fair_price_min'] + battery_info['fair_price_max']) / 2
        battery_cost = avg_battery_price * battery_quantity
        logger.info(f"Battery cost: {battery_quantity} × £{avg_battery_price} = £{battery_cost}")
    
    # Calculate solar panel cost (total price minus battery and installation)
    solar_panel_cost = total_price - battery_cost - installation_cost
    
    # Calculate price per kW for solar panels only
    if system_size > 0:
        price_per_kw = solar_panel_cost / system_size
    else:
        price_per_kw = 0
    
    logger.info(f"Cost breakdown: Solar £{solar_panel_cost}, Battery £{battery_cost}, Installation £{installation_cost}")
    logger.info(f"Price per kW (solar only): £{price_per_kw}")
    
    return {
        'solar_panel_cost': solar_panel_cost,
        'battery_cost': battery_cost,
        'installation_cost': installation_cost,
        'price_per_kw': price_per_kw
    }

def calculate_grade_and_verdict(costs, has_battery, battery_brand, battery_quantity, total_price):
    """
    Enhanced grading system that considers component-specific pricing
    """
    price_per_kw = costs['price_per_kw']
    solar_panel_cost = costs['solar_panel_cost']
    battery_cost = costs['battery_cost']
    
    # Check for suspiciously low prices (potential scam)
    if price_per_kw < 600:
        return 'F', 'Suspiciously low price - potential scam or hidden costs'
    
    # Grade solar panel pricing
    if price_per_kw <= SOLAR_PANEL_PRICING['excellent_max']:
        solar_grade = 'A'
        solar_verdict = 'Excellent value for solar panels'
    elif price_per_kw <= SOLAR_PANEL_PRICING['good_max']:
        solar_grade = 'B'
        solar_verdict = 'Good value for solar panels'
    elif price_per_kw <= SOLAR_PANEL_PRICING['fair_max']:
        solar_grade = 'C'
        solar_verdict = 'Fair price for solar panels'
    elif price_per_kw <= SOLAR_PANEL_PRICING['overpriced_max']:
        solar_grade = 'D'
        solar_verdict = 'Solar panels are overpriced'
    else:
        solar_grade = 'F'
        solar_verdict = 'Solar panels are severely overpriced'
    
    # Grade battery pricing if applicable
    battery_grade = 'N/A'
    battery_verdict = ''
    
    if has_battery and battery_brand and battery_brand in BATTERY_PRICING:
        battery_info = BATTERY_PRICING[battery_brand]
        expected_battery_cost = (battery_info['fair_price_min'] + battery_info['fair_price_max']) / 2 * battery_quantity
        
        # Calculate battery price variance
        battery_variance = (battery_cost - expected_battery_cost) / expected_battery_cost
        
        if battery_variance <= -0.1:  # 10% below fair price
            battery_grade = 'A'
            battery_verdict = 'Excellent battery pricing'
        elif battery_variance <= 0.1:  # Within 10% of fair price
            battery_grade = 'B'
            battery_verdict = 'Good battery pricing'
        elif battery_variance <= 0.25:  # 25% above fair price
            battery_grade = 'C'
            battery_verdict = 'Fair battery pricing'
        elif battery_variance <= 0.5:  # 50% above fair price
            battery_grade = 'D'
            battery_verdict = 'Battery is overpriced'
        else:
            battery_grade = 'F'
            battery_verdict = 'Battery is severely overpriced'
    
    # Combine grades for overall assessment
    grade_values = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'F': 1}
    
    if has_battery and battery_grade != 'N/A':
        # Average of solar and battery grades
        avg_grade_value = (grade_values[solar_grade] + grade_values[battery_grade]) / 2
        overall_verdict = f"{solar_verdict}. {battery_verdict}"
    else:
        # Solar only
        avg_grade_value = grade_values[solar_grade]
        overall_verdict = solar_verdict
    
    # Convert back to letter grade
    if avg_grade_value >= 4.5:
        overall_grade = 'A'
    elif avg_grade_value >= 3.5:
        overall_grade = 'B'
    elif avg_grade_value >= 2.5:
        overall_grade = 'C'
    elif avg_grade_value >= 1.5:
        overall_grade = 'D'
    else:
        overall_grade = 'F'
    
    return overall_grade, overall_verdict

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_status = "disconnected"
    
    return jsonify({
        "message": "Solar Verify Backend API",
        "status": "healthy",
        "database": db_status,
        "version": "2.0.0"
    })

@app.route('/api/analyze-quote', methods=['POST'])
def analyze_quote():
    """Enhanced quote analysis with component-specific pricing"""
    try:
        data = request.get_json()
        logger.info(f"Received analysis request: {data}")
        
        # Extract and validate data
        system_size = float(data.get('system_size', 0))
        has_battery = data.get('has_battery', False)
        battery_brand = data.get('battery_brand', '')
        battery_quantity = int(data.get('battery_quantity', 0))
        battery_size = float(data.get('battery_size', 0))
        total_battery_capacity = float(data.get('total_battery_capacity', 0))
        total_price = float(data.get('total_price', 0))
        
        # Validate required fields
        if system_size <= 0 or total_price <= 0:
            logger.warning(f"Invalid input: system_size={system_size}, total_price={total_price}")
            return jsonify({"error": "Invalid system size or price"}), 400
        
        # Validate battery data if battery is included
        if has_battery:
            if not battery_brand or battery_quantity <= 0 or battery_size <= 0:
                logger.warning(f"Invalid battery data: brand={battery_brand}, qty={battery_quantity}, size={battery_size}")
                return jsonify({"error": "Invalid battery information"}), 400
        
        # Calculate component costs
        costs = calculate_component_costs(
            system_size, has_battery, battery_brand, battery_quantity, total_price
        )
        
        # Calculate grade and verdict
        grade, verdict = calculate_grade_and_verdict(
            costs, has_battery, battery_brand, battery_quantity, total_price
        )
        
        # Prepare response
        response_data = {
            "system_size": system_size,
            "has_battery": has_battery,
            "battery_brand": battery_brand if has_battery else None,
            "battery_quantity": battery_quantity if has_battery else 0,
            "battery_size": battery_size if has_battery else 0,
            "total_battery_capacity": total_battery_capacity if has_battery else 0,
            "total_price": total_price,
            "solar_panel_cost": round(costs['solar_panel_cost'], 2),
            "battery_cost": round(costs['battery_cost'], 2),
            "installation_cost": round(costs['installation_cost'], 2),
            "price_per_kw": round(costs['price_per_kw'], 2),
            "grade": grade,
            "verdict": verdict
        }
        
        # Save to database (without email field)
        try:
            analysis = QuoteAnalysis(
                system_size=system_size,
                has_battery=has_battery,
                battery_brand=battery_brand if has_battery else None,
                battery_quantity=battery_quantity,
                battery_size=battery_size,
                total_battery_capacity=total_battery_capacity,
                total_price=total_price,
                price_per_kw=costs['price_per_kw'],
                solar_panel_cost=costs['solar_panel_cost'],
                battery_cost=costs['battery_cost'],
                installation_cost=costs['installation_cost'],
                grade=grade,
                verdict=verdict
            )
            
            db.session.add(analysis)
            db.session.commit()
            logger.info(f"Analysis saved to database with ID: {analysis.id}")
            
        except Exception as db_error:
            logger.error(f"Database save failed: {db_error}")
            # Continue with response even if database save fails
            db.session.rollback()
        
        logger.info(f"Analysis completed: Grade {grade}, Verdict: {verdict}")
        return jsonify(response_data)
        
    except ValueError as e:
        logger.error(f"Value error in analysis: {e}")
        return jsonify({"error": "Invalid data format"}), 400
    except Exception as e:
        logger.error(f"Unexpected error in analysis: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/register-email', methods=['POST'])
def register_email():
    """Register user email for follow-up"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email or '@' not in email:
            return jsonify({"error": "Invalid email address"}), 400
        
        # Check if email already exists
        existing = EmailRegistration.query.filter_by(email=email).first()
        if existing:
            logger.info(f"Email already registered: {email}")
            return jsonify({"message": "Email already registered", "status": "existing"})
        
        # Save new email
        registration = EmailRegistration(email=email)
        db.session.add(registration)
        db.session.commit()
        
        logger.info(f"New email registered: {email}")
        return jsonify({"message": "Email registered successfully", "status": "new"})
        
    except Exception as e:
        logger.error(f"Email registration error: {e}")
        db.session.rollback()
        return jsonify({"error": "Registration failed"}), 500

@app.route('/api/admin/emails', methods=['GET'])
def get_emails():
    """Admin endpoint to view collected emails"""
    try:
        emails = EmailRegistration.query.order_by(EmailRegistration.created_at.desc()).all()
        email_list = [
            {
                "id": email.id,
                "email": email.email,
                "created_at": email.created_at.isoformat()
            }
            for email in emails
        ]
        
        return jsonify({
            "total_emails": len(email_list),
            "emails": email_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return jsonify({"error": "Failed to fetch emails"}), 500

@app.route('/api/admin/analyses', methods=['GET'])
def get_analyses():
    """Admin endpoint to view quote analyses"""
    try:
        analyses = QuoteAnalysis.query.order_by(QuoteAnalysis.created_at.desc()).limit(100).all()
        analysis_list = [
            {
                "id": analysis.id,
                "system_size": analysis.system_size,
                "has_battery": analysis.has_battery,
                "battery_brand": analysis.battery_brand,
                "battery_quantity": analysis.battery_quantity,
                "total_price": analysis.total_price,
                "grade": analysis.grade,
                "verdict": analysis.verdict,
                "created_at": analysis.created_at.isoformat()
            }
            for analysis in analyses
        ]
        
        return jsonify({
            "total_analyses": len(analysis_list),
            "analyses": analysis_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching analyses: {e}")
        return jsonify({"error": "Failed to fetch analyses"}), 500

# Create tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

