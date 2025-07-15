from flask import Blueprint, request, jsonify
from src.models.component import db, QuoteAnalysis, PricingBenchmark, SolarPanel, Battery
from datetime import datetime
import math

quote_bp = Blueprint('quote', __name__)

@quote_bp.route('/analyze-quote', methods=['POST'])
def analyze_quote():
    """Analyze a solar quote and return grade and verdict"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(key in data for key in ['system_size', 'total_price']):
            return jsonify({'error': 'Missing required fields: system_size, total_price'}), 400
        
        system_size = float(data['system_size'])
        battery_size = float(data.get('battery_size', 0))
        total_price = float(data['total_price'])
        user_email = data.get('user_email')
        
        # Calculate price per kW
        price_per_kw = total_price / system_size
        
        # Perform analysis
        analysis_result = perform_quote_analysis(price_per_kw, system_size, battery_size)
        
        # Save analysis to database
        quote_analysis = QuoteAnalysis(
            user_email=user_email,
            system_size_kw=system_size,
            battery_size_kwh=battery_size if battery_size > 0 else None,
            total_price=total_price,
            price_per_kw=price_per_kw,
            grade=analysis_result['grade'],
            verdict=analysis_result['verdict'],
            analysis_type='free'
        )
        
        db.session.add(quote_analysis)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'analysis': {
                'grade': analysis_result['grade'],
                'verdict': analysis_result['verdict'],
                'price_per_kw': round(price_per_kw, 2),
                'system_size': system_size,
                'battery_size': battery_size,
                'total_price': total_price,
                'score': analysis_result['score'],
                'breakdown': analysis_result['breakdown']
            }
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid numeric values provided'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@quote_bp.route('/components/panels', methods=['GET'])
def get_panels():
    """Get solar panel database for component matching"""
    try:
        wattage = request.args.get('wattage', type=int)
        manufacturer = request.args.get('manufacturer', type=str)
        
        query = SolarPanel.query
        
        if wattage:
            # Find panels within ±50W of requested wattage
            query = query.filter(SolarPanel.wattage.between(wattage - 50, wattage + 50))
        
        if manufacturer:
            query = query.filter(SolarPanel.manufacturer.ilike(f'%{manufacturer}%'))
        
        panels = query.all()
        
        return jsonify({
            'success': True,
            'panels': [{
                'id': panel.id,
                'manufacturer': panel.manufacturer,
                'model': panel.model,
                'wattage': panel.wattage,
                'efficiency': panel.efficiency,
                'quality_tier': panel.quality_tier,
                'warranty_years': panel.warranty_years
            } for panel in panels]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@quote_bp.route('/components/batteries', methods=['GET'])
def get_batteries():
    """Get battery database for component matching"""
    try:
        capacity = request.args.get('capacity', type=float)
        manufacturer = request.args.get('manufacturer', type=str)
        
        query = Battery.query
        
        if capacity:
            # Find batteries within ±2kWh of requested capacity
            query = query.filter(Battery.capacity_kwh.between(capacity - 2, capacity + 2))
        
        if manufacturer:
            query = query.filter(Battery.manufacturer.ilike(f'%{manufacturer}%'))
        
        batteries = query.all()
        
        return jsonify({
            'success': True,
            'batteries': [{
                'id': battery.id,
                'manufacturer': battery.manufacturer,
                'model': battery.model,
                'capacity_kwh': battery.capacity_kwh,
                'usable_capacity_kwh': battery.usable_capacity_kwh,
                'quality_tier': battery.quality_tier,
                'warranty_years': battery.warranty_years,
                'cycles': battery.cycles
            } for battery in batteries]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@quote_bp.route('/pricing-benchmarks', methods=['GET'])
def get_pricing_benchmarks():
    """Get current pricing benchmarks"""
    try:
        benchmarks = PricingBenchmark.query.all()
        
        return jsonify({
            'success': True,
            'benchmarks': [{
                'installer_type': benchmark.installer_type,
                'price_per_kw_min': benchmark.price_per_kw_min,
                'price_per_kw_max': benchmark.price_per_kw_max,
                'description': benchmark.description
            } for benchmark in benchmarks]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def perform_quote_analysis(price_per_kw, system_size, battery_size):
    """Core quote analysis logic"""
    
    # Pricing analysis (40 points)
    pricing_score = calculate_pricing_score(price_per_kw)
    
    # System sizing analysis (30 points)
    sizing_score = calculate_sizing_score(system_size, battery_size)
    
    # Value analysis (30 points)
    value_score = calculate_value_score(price_per_kw, system_size, battery_size)
    
    # Calculate total score
    total_score = pricing_score + sizing_score + value_score
    
    # Determine grade
    if total_score >= 90:
        grade = 'A'
    elif total_score >= 80:
        grade = 'B'
    elif total_score >= 70:
        grade = 'C'
    elif total_score >= 60:
        grade = 'D'
    else:
        grade = 'F'
    
    # Generate verdict
    verdict = generate_verdict(grade, price_per_kw, system_size, battery_size)
    
    return {
        'grade': grade,
        'verdict': verdict,
        'score': total_score,
        'breakdown': {
            'pricing': pricing_score,
            'sizing': sizing_score,
            'value': value_score
        }
    }

def calculate_pricing_score(price_per_kw):
    """Calculate pricing score based on UK market rates"""
    if price_per_kw <= 1400:
        return 40  # Excellent value
    elif price_per_kw <= 1800:
        return 35  # Very good value
    elif price_per_kw <= 2200:
        return 25  # Fair value
    elif price_per_kw <= 2800:
        return 15  # Above average
    else:
        return 5   # Overpriced

def calculate_sizing_score(system_size, battery_size):
    """Calculate system sizing appropriateness"""
    score = 20  # Base score
    
    # Typical UK home needs 3-8kW
    if 3 <= system_size <= 8:
        score += 10  # Well-sized system
    elif system_size < 3:
        score += 5   # Small but acceptable
    elif system_size > 12:
        score -= 5   # Very large system
    
    # Battery sizing bonus
    if battery_size > 0:
        if 10 <= battery_size <= 20:
            score += 5  # Good battery size
        elif battery_size > 20:
            score += 3  # Large battery
    
    return min(score, 30)

def calculate_value_score(price_per_kw, system_size, battery_size):
    """Calculate overall value proposition"""
    score = 15  # Base score
    
    # System size value
    if system_size >= 6:
        score += 5  # Larger systems often better value
    
    # Battery value
    if battery_size > 0:
        battery_value_per_kwh = 800  # Rough £/kWh for batteries
        if price_per_kw < 2000:  # If overall price is good
            score += 10  # Good value with battery
        else:
            score += 5   # Battery adds value but system pricey
    
    # Price consistency check
    if price_per_kw <= 1600:
        score += 5  # Consistently good pricing
    
    return min(score, 30)

def generate_verdict(grade, price_per_kw, system_size, battery_size):
    """Generate human-readable verdict"""
    
    if grade == 'A':
        if battery_size > 0:
            return f"Excellent value system with battery storage. At £{price_per_kw:.0f}/kW, this is competitive pricing for a {system_size}kW system with {battery_size}kWh battery."
        else:
            return f"Excellent value for money. £{price_per_kw:.0f}/kW is competitive pricing for a {system_size}kW solar system."
    
    elif grade == 'B':
        return f"Good value system. £{price_per_kw:.0f}/kW is within acceptable market range for a {system_size}kW system."
    
    elif grade == 'C':
        return f"Fair pricing but room for improvement. £{price_per_kw:.0f}/kW is above average - consider getting additional quotes."
    
    elif grade == 'D':
        return f"Above market rate. £{price_per_kw:.0f}/kW is expensive for a {system_size}kW system - definitely get more quotes."
    
    else:  # Grade F
        return f"Overpriced system. £{price_per_kw:.0f}/kW is significantly above market rate - avoid this installer."

