#!/usr/bin/env python3
"""
Seed the database with real solar component data and pricing benchmarks
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.main import app
from src.models.component import db, SolarPanel, Battery, Inverter, PricingBenchmark

def seed_solar_panels():
    """Add real solar panel data"""
    panels = [
        # Premium Tier
        SolarPanel(
            manufacturer="Longi", model="LR5-72HIH-515M", wattage=515, efficiency=21.2,
            technology="Monocrystalline", warranty_years=25, quality_tier="Premium",
            price_per_watt=0.45, dimensions_length=2.26, dimensions_width=1.13
        ),
        SolarPanel(
            manufacturer="JA Solar", model="JAM72S30-545/MR", wattage=545, efficiency=21.0,
            technology="Monocrystalline", warranty_years=25, quality_tier="Premium",
            price_per_watt=0.42, dimensions_length=2.27, dimensions_width=1.13
        ),
        SolarPanel(
            manufacturer="Trina Solar", model="TSM-NEG21C.20-550W", wattage=550, efficiency=21.3,
            technology="Monocrystalline", warranty_years=25, quality_tier="Premium",
            price_per_watt=0.44, dimensions_length=2.28, dimensions_width=1.13
        ),
        
        # Excellent Tier
        SolarPanel(
            manufacturer="Canadian Solar", model="CS3W-450MS", wattage=450, efficiency=20.7,
            technology="Monocrystalline", warranty_years=25, quality_tier="Excellent",
            price_per_watt=0.38, dimensions_length=2.11, dimensions_width=1.05
        ),
        SolarPanel(
            manufacturer="Jinko Solar", model="JKM480M-7RL3-V", wattage=480, efficiency=20.8,
            technology="Monocrystalline", warranty_years=25, quality_tier="Excellent",
            price_per_watt=0.40, dimensions_length=2.17, dimensions_width=1.05
        ),
        
        # Good Tier
        SolarPanel(
            manufacturer="Risen Energy", model="RSM144-6-400M", wattage=400, efficiency=20.5,
            technology="Monocrystalline", warranty_years=25, quality_tier="Good",
            price_per_watt=0.35, dimensions_length=2.01, dimensions_width=1.00
        ),
        SolarPanel(
            manufacturer="Astronergy", model="CHSM6610M-HC-420", wattage=420, efficiency=20.3,
            technology="Monocrystalline", warranty_years=25, quality_tier="Good",
            price_per_watt=0.36, dimensions_length=2.09, dimensions_width=1.05
        ),
        
        # Standard Tier
        SolarPanel(
            manufacturer="Phono Solar", model="PS350M-24/TH", wattage=350, efficiency=19.8,
            technology="Monocrystalline", warranty_years=20, quality_tier="Standard",
            price_per_watt=0.32, dimensions_length=1.96, dimensions_width=0.99
        ),
    ]
    
    for panel in panels:
        existing = SolarPanel.query.filter_by(manufacturer=panel.manufacturer, model=panel.model).first()
        if not existing:
            db.session.add(panel)

def seed_batteries():
    """Add real battery data"""
    batteries = [
        # Premium Tier
        Battery(
            manufacturer="Tesla", model="Powerwall 3", capacity_kwh=13.5, usable_capacity_kwh=13.5,
            technology="LiFePO4", warranty_years=10, cycles=6000, quality_tier="Premium",
            price_per_kwh=800, round_trip_efficiency=97.5
        ),
        Battery(
            manufacturer="Enphase", model="IQ Battery 5P", capacity_kwh=5.0, usable_capacity_kwh=4.96,
            technology="LiFePO4", warranty_years=15, cycles=6000, quality_tier="Premium",
            price_per_kwh=900, round_trip_efficiency=96.0
        ),
        
        # Excellent Tier
        Battery(
            manufacturer="GivEnergy", model="Giv-Bat 9.5", capacity_kwh=9.5, usable_capacity_kwh=8.55,
            technology="LiFePO4", warranty_years=12, cycles=6000, quality_tier="Excellent",
            price_per_kwh=650, round_trip_efficiency=95.0
        ),
        Battery(
            manufacturer="PureDrive", model="PureStorage II 10kWh", capacity_kwh=10.0, usable_capacity_kwh=9.0,
            technology="LiFePO4", warranty_years=10, cycles=6000, quality_tier="Excellent",
            price_per_kwh=700, round_trip_efficiency=94.0
        ),
        
        # Good Tier
        Battery(
            manufacturer="Fox ESS", model="EP11", capacity_kwh=20.72, usable_capacity_kwh=18.65,
            technology="LiFePO4", warranty_years=10, cycles=6000, quality_tier="Good",
            price_per_kwh=550, round_trip_efficiency=93.0
        ),
        Battery(
            manufacturer="Fox ESS", model="EP10", capacity_kwh=10.36, usable_capacity_kwh=9.32,
            technology="LiFePO4", warranty_years=10, cycles=6000, quality_tier="Good",
            price_per_kwh=580, round_trip_efficiency=93.0
        ),
        Battery(
            manufacturer="LG Chem", model="RESU10H", capacity_kwh=9.8, usable_capacity_kwh=8.8,
            technology="Li-ion", warranty_years=10, cycles=6000, quality_tier="Good",
            price_per_kwh=720, round_trip_efficiency=94.5
        ),
        
        # Standard Tier
        Battery(
            manufacturer="Pylontech", model="US3000C", capacity_kwh=3.55, usable_capacity_kwh=3.2,
            technology="LiFePO4", warranty_years=10, cycles=6000, quality_tier="Standard",
            price_per_kwh=500, round_trip_efficiency=92.0
        ),
    ]
    
    for battery in batteries:
        existing = Battery.query.filter_by(manufacturer=battery.manufacturer, model=battery.model).first()
        if not existing:
            db.session.add(battery)

def seed_inverters():
    """Add real inverter data"""
    inverters = [
        # Premium Tier
        Inverter(
            manufacturer="SolarEdge", model="SE5000H-RWS", power_rating_kw=5.0, efficiency=97.3,
            inverter_type="Power Optimizers", warranty_years=25, quality_tier="Premium",
            price=1200, mppt_trackers=1
        ),
        Inverter(
            manufacturer="Enphase", model="IQ8PLUS-72-2-US", power_rating_kw=0.295, efficiency=97.0,
            inverter_type="Microinverters", warranty_years=25, quality_tier="Premium",
            price=180, mppt_trackers=1
        ),
        
        # Excellent Tier
        Inverter(
            manufacturer="GivEnergy", model="GIV-5.0-AC", power_rating_kw=5.0, efficiency=97.6,
            inverter_type="String", warranty_years=10, quality_tier="Excellent",
            price=800, mppt_trackers=2
        ),
        Inverter(
            manufacturer="Solis", model="S5-GR1P6K", power_rating_kw=6.0, efficiency=98.1,
            inverter_type="String", warranty_years=10, quality_tier="Excellent",
            price=650, mppt_trackers=2
        ),
        
        # Good Tier
        Inverter(
            manufacturer="Fox ESS", model="H1-5.0-E", power_rating_kw=5.0, efficiency=97.8,
            inverter_type="String", warranty_years=10, quality_tier="Good",
            price=550, mppt_trackers=2
        ),
        Inverter(
            manufacturer="Growatt", model="SPH5000", power_rating_kw=5.0, efficiency=97.6,
            inverter_type="String", warranty_years=10, quality_tier="Good",
            price=600, mppt_trackers=2
        ),
    ]
    
    for inverter in inverters:
        existing = Inverter.query.filter_by(manufacturer=inverter.manufacturer, model=inverter.model).first()
        if not existing:
            db.session.add(inverter)

def seed_pricing_benchmarks():
    """Add current UK pricing benchmarks"""
    benchmarks = [
        PricingBenchmark(
            installer_type="Volume",
            price_per_kw_min=1200,
            price_per_kw_max=1600,
            description="Large national installers (Octopus Energy, British Gas, etc.)"
        ),
        PricingBenchmark(
            installer_type="Local",
            price_per_kw_min=1400,
            price_per_kw_max=2200,
            description="Local and regional installers"
        ),
        PricingBenchmark(
            installer_type="Premium",
            price_per_kw_min=2000,
            price_per_kw_max=2800,
            description="Premium installers with high-end components"
        ),
    ]
    
    for benchmark in benchmarks:
        existing = PricingBenchmark.query.filter_by(installer_type=benchmark.installer_type).first()
        if existing:
            # Update existing benchmark
            existing.price_per_kw_min = benchmark.price_per_kw_min
            existing.price_per_kw_max = benchmark.price_per_kw_max
            existing.description = benchmark.description
            existing.last_updated = benchmark.last_updated
        else:
            db.session.add(benchmark)

def main():
    """Run the seeding process"""
    with app.app_context():
        print("🌱 Seeding database with component data...")
        
        # Clear existing data (optional - comment out to preserve data)
        # db.drop_all()
        # db.create_all()
        
        seed_solar_panels()
        print("✅ Solar panels seeded")
        
        seed_batteries()
        print("✅ Batteries seeded")
        
        seed_inverters()
        print("✅ Inverters seeded")
        
        seed_pricing_benchmarks()
        print("✅ Pricing benchmarks seeded")
        
        db.session.commit()
        print("🎉 Database seeding completed!")
        
        # Print summary
        panel_count = SolarPanel.query.count()
        battery_count = Battery.query.count()
        inverter_count = Inverter.query.count()
        benchmark_count = PricingBenchmark.query.count()
        
        print(f"\n📊 Database Summary:")
        print(f"   Solar Panels: {panel_count}")
        print(f"   Batteries: {battery_count}")
        print(f"   Inverters: {inverter_count}")
        print(f"   Pricing Benchmarks: {benchmark_count}")

if __name__ == "__main__":
    main()

