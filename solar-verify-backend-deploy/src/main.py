import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.models.component import SolarPanel, Battery, Inverter, PricingBenchmark, QuoteAnalysis
from src.routes.user import user_bp
from src.routes.quote_analyzer import quote_bp
from src.routes.email_tracking import email_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')

# Enable CORS for all routes
CORS(app)

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(quote_bp, url_prefix='/api')
app.register_blueprint(email_bp, url_prefix='/api')

# Database configuration - use PostgreSQL in production, SQLite in development
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Production - use PostgreSQL from Railway
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Development - use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Seed database if it's empty (first deployment)
    if SolarPanel.query.count() == 0:
        from src.seed_data import seed_solar_panels, seed_batteries, seed_inverters, seed_pricing_benchmarks
        print("🌱 Seeding database for first deployment...")
        seed_solar_panels()
        seed_batteries()
        seed_inverters()
        seed_pricing_benchmarks()
        db.session.commit()
        print("✅ Database seeded successfully!")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "Solar Verify API is running! 🌞", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
