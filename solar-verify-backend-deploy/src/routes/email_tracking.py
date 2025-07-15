from flask import Blueprint, request, jsonify
from src.models.user import db, User
from src.models.component import QuoteAnalysis
from datetime import datetime, timedelta
import re

email_bp = Blueprint('email', __name__)

@email_bp.route('/track-usage', methods=['POST'])
def track_usage():
    """Track user usage and check limits"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')  # Could be IP address or session ID
        email = data.get('email')
        
        # Check usage limits
        usage_info = check_usage_limits(user_id, email)
        
        return jsonify({
            'success': True,
            'usage': usage_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@email_bp.route('/register-email', methods=['POST'])
def register_email():
    """Register user email for additional free checks"""
    try:
        data = request.get_json()
        email = data.get('email')
        user_id = data.get('user_id')
        
        if not email or not is_valid_email(email):
            return jsonify({'error': 'Valid email address required'}), 400
        
        # Check if user already exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user
            user = User(
                email=email,
                free_checks_used=0,
                free_checks_limit=3,  # 3 total free checks with email
                created_at=datetime.utcnow()
            )
            db.session.add(user)
        
        # Update user_id if provided
        if user_id:
            user.user_id = user_id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Email registered successfully',
            'user': {
                'email': user.email,
                'free_checks_remaining': max(0, user.free_checks_limit - user.free_checks_used),
                'can_use_free': user.free_checks_used < user.free_checks_limit
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@email_bp.route('/check-email-status', methods=['POST'])
def check_email_status():
    """Check if email is registered and usage status"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            return jsonify({
                'success': True,
                'registered': True,
                'user': {
                    'email': user.email,
                    'free_checks_used': user.free_checks_used,
                    'free_checks_remaining': max(0, user.free_checks_limit - user.free_checks_used),
                    'can_use_free': user.free_checks_used < user.free_checks_limit,
                    'total_analyses': QuoteAnalysis.query.filter_by(user_email=email).count()
                }
            })
        else:
            return jsonify({
                'success': True,
                'registered': False
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@email_bp.route('/user-analytics', methods=['GET'])
def user_analytics():
    """Get user analytics and usage patterns"""
    try:
        email = request.args.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's quote analyses
        analyses = QuoteAnalysis.query.filter_by(user_email=email).order_by(QuoteAnalysis.created_at.desc()).all()
        
        # Calculate analytics
        total_analyses = len(analyses)
        avg_system_size = sum(a.system_size_kw for a in analyses) / total_analyses if total_analyses > 0 else 0
        avg_price_per_kw = sum(a.price_per_kw for a in analyses) / total_analyses if total_analyses > 0 else 0
        
        grade_distribution = {}
        for analysis in analyses:
            grade_distribution[analysis.grade] = grade_distribution.get(analysis.grade, 0) + 1
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_analyses': total_analyses,
                'avg_system_size': round(avg_system_size, 1),
                'avg_price_per_kw': round(avg_price_per_kw, 2),
                'grade_distribution': grade_distribution,
                'recent_analyses': [{
                    'date': analysis.created_at.isoformat(),
                    'system_size': analysis.system_size_kw,
                    'grade': analysis.grade,
                    'price_per_kw': analysis.price_per_kw
                } for analysis in analyses[:5]]
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def check_usage_limits(user_id, email=None):
    """Check usage limits for anonymous or registered users"""
    
    if email:
        # Registered user - check database limits
        user = User.query.filter_by(email=email).first()
        if user:
            return {
                'type': 'registered',
                'email': email,
                'checks_used': user.free_checks_used,
                'checks_limit': user.free_checks_limit,
                'can_use_free': user.free_checks_used < user.free_checks_limit,
                'needs_email': False,
                'needs_upgrade': user.free_checks_used >= user.free_checks_limit
            }
    
    # Anonymous user - check recent analyses by user_id (could be IP/session)
    if user_id:
        # Count analyses in last 24 hours for this user_id
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_count = QuoteAnalysis.query.filter(
            QuoteAnalysis.created_at >= yesterday,
            QuoteAnalysis.user_email == user_id  # Using email field for user_id tracking
        ).count()
        
        return {
            'type': 'anonymous',
            'checks_used': recent_count,
            'checks_limit': 1,  # Only 1 free check for anonymous users
            'can_use_free': recent_count < 1,
            'needs_email': recent_count >= 1,
            'needs_upgrade': False
        }
    
    # New anonymous user
    return {
        'type': 'new',
        'checks_used': 0,
        'checks_limit': 1,
        'can_use_free': True,
        'needs_email': False,
        'needs_upgrade': False
    }

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

