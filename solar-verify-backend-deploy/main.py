from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        'timestamp': '2025-08-12T10:00:00Z',
        'version': '2.0.0-railway-compatible'
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

