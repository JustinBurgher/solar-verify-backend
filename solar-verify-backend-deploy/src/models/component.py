from flask_sqlalchemy import SQLAlchemy
from src.models.user import db
from datetime import datetime

class SolarPanel(db.Model):
    __tablename__ = 'solar_panels'
    
    id = db.Column(db.Integer, primary_key=True)
    manufacturer = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    wattage = db.Column(db.Integer, nullable=False)
    efficiency = db.Column(db.Float, nullable=False)  # Percentage
    technology = db.Column(db.String(50), nullable=False)  # Monocrystalline, Polycrystalline, etc.
    warranty_years = db.Column(db.Integer, nullable=False)
    quality_tier = db.Column(db.String(20), nullable=False)  # Premium, Excellent, Good, Standard
    price_per_watt = db.Column(db.Float, nullable=True)  # £ per watt
    dimensions_length = db.Column(db.Float, nullable=True)  # meters
    dimensions_width = db.Column(db.Float, nullable=True)  # meters
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SolarPanel {self.manufacturer} {self.model} {self.wattage}W>'

class Battery(db.Model):
    __tablename__ = 'batteries'
    
    id = db.Column(db.Integer, primary_key=True)
    manufacturer = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    capacity_kwh = db.Column(db.Float, nullable=False)
    usable_capacity_kwh = db.Column(db.Float, nullable=False)
    technology = db.Column(db.String(50), nullable=False)  # LiFePO4, Li-ion, etc.
    warranty_years = db.Column(db.Integer, nullable=False)
    cycles = db.Column(db.Integer, nullable=False)  # Number of charge cycles
    quality_tier = db.Column(db.String(20), nullable=False)  # Premium, Excellent, Good, Standard
    price_per_kwh = db.Column(db.Float, nullable=True)  # £ per kWh
    round_trip_efficiency = db.Column(db.Float, nullable=True)  # Percentage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Battery {self.manufacturer} {self.model} {self.capacity_kwh}kWh>'

class Inverter(db.Model):
    __tablename__ = 'inverters'
    
    id = db.Column(db.Integer, primary_key=True)
    manufacturer = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    power_rating_kw = db.Column(db.Float, nullable=False)
    efficiency = db.Column(db.Float, nullable=False)  # Percentage
    inverter_type = db.Column(db.String(50), nullable=False)  # String, Power Optimizers, Microinverters
    warranty_years = db.Column(db.Integer, nullable=False)
    quality_tier = db.Column(db.String(20), nullable=False)  # Premium, Excellent, Good, Standard
    price = db.Column(db.Float, nullable=True)  # £
    mppt_trackers = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Inverter {self.manufacturer} {self.model} {self.power_rating_kw}kW>'

class PricingBenchmark(db.Model):
    __tablename__ = 'pricing_benchmarks'
    
    id = db.Column(db.Integer, primary_key=True)
    installer_type = db.Column(db.String(50), nullable=False)  # Volume, Local, Premium
    price_per_kw_min = db.Column(db.Float, nullable=False)  # £ per kW
    price_per_kw_max = db.Column(db.Float, nullable=False)  # £ per kW
    description = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PricingBenchmark {self.installer_type} £{self.price_per_kw_min}-{self.price_per_kw_max}/kW>'

class QuoteAnalysis(db.Model):
    __tablename__ = 'quote_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=True)
    system_size_kw = db.Column(db.Float, nullable=False)
    battery_size_kwh = db.Column(db.Float, nullable=True)
    total_price = db.Column(db.Float, nullable=False)
    price_per_kw = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(2), nullable=False)  # A, B, C, D, F
    verdict = db.Column(db.Text, nullable=False)
    analysis_type = db.Column(db.String(20), nullable=False)  # free, basic, pro, complete
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<QuoteAnalysis {self.system_size_kw}kW Grade:{self.grade}>'

