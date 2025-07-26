from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///solar_verify.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class EmailRegistration(db.Model):
    __tablename__ = 'email_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)

class QuoteAnalysis(db.Model):
    __tablename__ = 'quote_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=True)
    system_size = db.Column(db.Float, nullable=False)
    battery_size = db.Column(db.Float, nullable=True)
    total_price = db.Column(db.Float, nullable=False)
    price_per_kw = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    verdict = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Routes
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Solar Verify Backend API',
        'version': '1.0.0',
        'database': 'connected' if database_url else 'local'
    })

@app.route('/api/register-email', methods=['POST'])
def register_email():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Check if email already exists
        existing = EmailRegistration.query.filter_by(email=email).first()
        if existing:
            return jsonify({
                'success': True,
                'message': 'Email already registered',
                'usage_count': existing.usage_count
            })
        
        # Create new email registration
        new_email = EmailRegistration(email=email, usage_count=0)
        db.session.add(new_email)
        db.session.commit()
        
        logger.info(f"New email registered: {email}")
        
        return jsonify({
            'success': True,
            'message': 'Email registered successfully',
            'usage_count': 0
        })
        
    except Exception as e:
        logger.error(f"Error registering email: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/track-usage', methods=['POST'])
def track_usage():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Find email registration
        email_reg = EmailRegistration.query.filter_by(email=email).first()
        if not email_reg:
            return jsonify({'error': 'Email not found'}), 404
        
        # Increment usage count
        email_reg.usage_count += 1
        email_reg.last_used = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Usage tracked for {email}: {email_reg.usage_count}")
        
        return jsonify({
            'success': True,
            'usage_count': email_reg.usage_count
        })
        
    except Exception as e:
        logger.error(f"Error tracking usage: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/analyze-quote', methods=['POST'])
def analyze_quote():
    try:
        data = request.get_json()
        
        # Extract quote data
        system_size = float(data.get('system_size', 0))
        battery_size = float(data.get('battery_size', 0)) if data.get('battery_size') else None
        total_price = float(data.get('total_price', 0))
        email = data.get('email', '').strip().lower() if data.get('email') else None
        
        if system_size <= 0 or total_price <= 0:
            return jsonify({'error': 'Invalid system size or price'}), 400
        
        # Calculate price per kW
        price_per_kw = total_price / system_size
        
        # Simple grading logic (can be enhanced later)
        if price_per_kw < 1000:
            grade = 'F'
            verdict = 'Suspiciously low - verify legitimacy'
        elif price_per_kw < 1400:
            grade = 'A'
            verdict = 'Excellent value'
        elif price_per_kw < 1800:
            grade = 'B'
            verdict = 'Good value'
        elif price_per_kw < 2200:
            grade = 'C'
            verdict = 'Fair price'
        elif price_per_kw < 2800:
            grade = 'D'
            verdict = 'Overpriced - get alternative quotes'
        else:
            grade = 'F'
            verdict = 'Severely overpriced - avoid'
        
        # Save analysis to database
        analysis = QuoteAnalysis(
            email=email,
            system_size=system_size,
            battery_size=battery_size,
            total_price=total_price,
            price_per_kw=price_per_kw,
            grade=grade,
            verdict=verdict
        )
        db.session.add(analysis)
        db.session.commit()
        
        logger.info(f"Quote analyzed: {system_size}kW, £{total_price}, Grade {grade}")
        
        return jsonify({
            'success': True,
            'analysis': {
                'system_size': system_size,
                'battery_size': battery_size,
                'total_price': total_price,
                'price_per_kw': round(price_per_kw, 2),
                'grade': grade,
                'verdict': verdict,
                'components': {
                    'panel_quality': 'Standard',
                    'battery_quality': 'Standard' if battery_size else None,
                    'system_sizing': 'Appropriate'
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error analyzing quote: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin/emails', methods=['GET'])
def get_emails():
    """Admin endpoint to view collected emails"""
    try:
        emails = EmailRegistration.query.order_by(EmailRegistration.created_at.desc()).all()
        
        email_list = []
        for email in emails:
            email_list.append({
                'email': email.email,
                'created_at': email.created_at.isoformat(),
                'usage_count': email.usage_count,
                'last_used': email.last_used.isoformat() if email.last_used else None
            })
        
        return jsonify({
            'success': True,
            'total_emails': len(email_list),
            'emails': email_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin/analytics', methods=['GET'])
def get_analytics():
    """Admin endpoint for basic analytics"""
    try:
        total_emails = EmailRegistration.query.count()
        total_analyses = QuoteAnalysis.query.count()
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_emails = EmailRegistration.query.filter(EmailRegistration.created_at >= week_ago).count()
        recent_analyses = QuoteAnalysis.query.filter(QuoteAnalysis.created_at >= week_ago).count()
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_emails': total_emails,
                'total_analyses': total_analyses,
                'recent_emails': recent_emails,
                'recent_analyses': recent_analyses
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

