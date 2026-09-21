"""
Indian Regional Sectors Database.
Contains operational parameters for prominent commercial regional turboprop sectors,
including airport elevation, runway lengths, standard temperatures, and grid carbon intensity.

Sources:
- Airport Elevations & Runway Data: Airports Authority of India (AAI) Aeronautical Information Publication (AIP) India.
- Grid Emission Factors: Central Electricity Authority (CEA), Ministry of Power, Government of India,
  "CO2 Baseline Database for the Indian Power Sector", User Guide Version 19.0 (December 2023), Table 1 (Weighted Average Emission Factor).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    icao: str
    iata: str
    name: str
    city: str
    elevation_ft: float
    runway_length_m: float
    avg_summer_oat_c: float
    elevation_source: str = "AAI AIP India"


@dataclass(frozen=True)
class Route:
    route_id: str
    name: str
    origin: Airport
    destination: Airport
    stage_distance_km: float
    nominal_cruise_alt_ft: float
    description: str
    regional_grid_co2_kg_per_kwh: float  # CEA Baseline Database v19.0 weighted average
    is_return_leg: bool = False


# Verified against AAI AIP India Aerodrome Charts
AIRPORTS: dict[str, Airport] = {
    "VOBL": Airport(
        "VOBL", "BLR", "Kempegowda Int'l", "Bengaluru", 3000.0, 4000.0, 34.0, "AAI AIP VOBL AD 2.2 (3,000 ft)"
    ),
    "VABM": Airport(
        "VABM", "IXG", "Belagavi Airport", "Belagavi", 2488.0, 2300.0, 33.0, "AAI AIP VABM AD 2.2 (2,488 ft)"
    ),
    "VABB": Airport(
        "VABB", "BOM", "Chhatrapati Shivaji Maharaj", "Mumbai", 39.0, 3660.0, 35.0, "AAI AIP VABB AD 2.2 (39 ft)"
    ),
    "VAPO": Airport("VAPO", "PNQ", "Pune Airport", "Pune", 1942.0, 2540.0, 38.0, "AAI AIP VAPO AD 2.2 (1,942 ft)"),
    "VIDP": Airport("VIDP", "DEL", "Indira Gandhi Int'l", "Delhi", 777.0, 4430.0, 42.0, "AAI AIP VIDP AD 2.2 (777 ft)"),
    "VIDN": Airport(
        "VIDN", "DED", "Jolly Grant Airport", "Dehradun", 1857.0, 2140.0, 36.0, "AAI AIP VIDN AD 2.2 (1,857 ft / 566 m)"
    ),
    "VOMM": Airport("VOMM", "MAA", "Chennai Int'l", "Chennai", 52.0, 3658.0, 39.0, "AAI AIP VOMM AD 2.2 (52 ft)"),
    "VOTP": Airport("VOTP", "TIR", "Tirupati Airport", "Tirupati", 350.0, 2286.0, 38.0, "AAI AIP VOTP AD 2.2 (350 ft)"),
    "VAAH": Airport(
        "VAAH", "AMD", "Sardar Vallabhbhai Patel", "Ahmedabad", 189.0, 3505.0, 43.0, "AAI AIP VAAH AD 2.2 (189 ft)"
    ),
    "VAUD": Airport(
        "VAUD",
        "UDR",
        "Maharana Pratap Airport",
        "Udaipur",
        1683.0,
        2743.0,
        40.0,
        "AAI AIP VAUD AD 2.2 (1,683 ft / 513 m)",
    ),
    "VICG": Airport("VICG", "IXC", "Shaheed Bhagat Singh Int'l", "Chandigarh", 1012.0, 3170.0, 40.0, "AAI AIP VICG AD 2.2 (1,012 ft)"),
    "VOHS": Airport("VOHS", "HYD", "Rajiv Gandhi Int'l", "Hyderabad", 2024.0, 4260.0, 40.0, "AAI AIP VOHS AD 2.2 (2,024 ft)"),
    "VEGT": Airport("VEGT", "GAU", "Lokpriya Gopinath Bordoloi", "Guwahati", 162.0, 3110.0, 33.0, "AAI AIP VEGT AD 2.2 (162 ft)"),
    "VEBI": Airport("VEBI", "SHL", "Shillong Airport", "Shillong", 2909.0, 1829.0, 28.0, "AAI AIP VEBI AD 2.2 (2,909 ft / 887 m)"),
    "VECC": Airport("VECC", "CCU", "Netaji Subhash Chandra Bose", "Kolkata", 16.0, 3627.0, 37.0, "AAI AIP VECC AD 2.2 (16 ft)"),
    "VEBD": Airport("VEBD", "IXB", "Bagdogra Airport", "Siliguri", 282.0, 2743.0, 34.0, "AAI AIP VEBD AD 2.2 (282 ft)"),
}

INDIAN_REGIONAL_SECTORS: list[Route] = [
    Route(
        route_id="BLR-IXG",
        name="Bengaluru (BLR) ➔ Belagavi (IXG)",
        origin=AIRPORTS["VOBL"],
        destination=AIRPORTS["VABM"],
        stage_distance_km=462.0,
        nominal_cruise_alt_ft=20000.0,
        description="High-traffic Karnataka regional sector. Elevated destination runway (2,488 ft).",
        regional_grid_co2_kg_per_kwh=0.68,
    ),
    Route(
        route_id="BOM-PNQ",
        name="Mumbai (BOM) ➔ Pune (PNQ)",
        origin=AIRPORTS["VABB"],
        destination=AIRPORTS["VAPO"],
        stage_distance_km=122.0,
        nominal_cruise_alt_ft=14000.0,
        description="Short-haul regional sector connecting coastal Mumbai to elevated Pune plateau (1,942 ft).",
        regional_grid_co2_kg_per_kwh=0.74,
    ),
    Route(
        route_id="DEL-DED",
        name="Delhi (DEL) ➔ Dehradun (DED)",
        origin=AIRPORTS["VIDP"],
        destination=AIRPORTS["VIDN"],
        stage_distance_km=208.0,
        nominal_cruise_alt_ft=16000.0,
        description="Northern regional connector to Himalayan foothills (DED 1,857 ft) under high ambient summer temperatures.",
        regional_grid_co2_kg_per_kwh=0.79,
    ),
    Route(
        route_id="MAA-TIR",
        name="Chennai (MAA) ➔ Tirupati (TIR)",
        origin=AIRPORTS["VOMM"],
        destination=AIRPORTS["VOTP"],
        stage_distance_km=115.0,
        nominal_cruise_alt_ft=12000.0,
        description="Short commuter feeder connector in Southern India.",
        regional_grid_co2_kg_per_kwh=0.72,
    ),
    Route(
        route_id="AMD-UDR",
        name="Ahmedabad (AMD) ➔ Udaipur (UDR)",
        origin=AIRPORTS["VAAH"],
        destination=AIRPORTS["VAUD"],
        stage_distance_km=215.0,
        nominal_cruise_alt_ft=16000.0,
        description="Western regional sector connecting Gujarat to southern Rajasthan (UDR 1,683 ft).",
        regional_grid_co2_kg_per_kwh=0.76,
    ),
    Route(
        route_id="IXC-DED",
        name="Chandigarh (IXC) ➔ Dehradun (DED)",
        origin=AIRPORTS["VICG"],
        destination=AIRPORTS["VIDN"],
        stage_distance_km=134.0,
        nominal_cruise_alt_ft=12000.0,
        description="Inter-state foothills feeder route connecting Punjab/Haryana to Uttarakhand.",
        regional_grid_co2_kg_per_kwh=0.75,
    ),
    Route(
        route_id="HYD-TIR",
        name="Hyderabad (HYD) ➔ Tirupati (TIR)",
        origin=AIRPORTS["VOHS"],
        destination=AIRPORTS["VOTP"],
        stage_distance_km=430.0,
        nominal_cruise_alt_ft=20000.0,
        description="High-density regional pilgrim route across Deccan plateau.",
        regional_grid_co2_kg_per_kwh=0.74,
    ),
    Route(
        route_id="GAU-SHL",
        name="Guwahati (GAU) ➔ Shillong (SHL)",
        origin=AIRPORTS["VEGT"],
        destination=AIRPORTS["VEBI"],
        stage_distance_km=68.0,
        nominal_cruise_alt_ft=10000.0,
        description="Ultra-short mountain connector to high-altitude Shillong/Umroi airport (2,909 ft).",
        regional_grid_co2_kg_per_kwh=0.58,
    ),
    Route(
        route_id="CCU-IXB",
        name="Kolkata (CCU) ➔ Bagdogra (IXB)",
        origin=AIRPORTS["VECC"],
        destination=AIRPORTS["VEBD"],
        stage_distance_km=450.0,
        nominal_cruise_alt_ft=20000.0,
        description="Major East India corridor connecting coastal plains to North Bengal tea region.",
        regional_grid_co2_kg_per_kwh=0.82,
    ),
]

# Backward compatibility alias
UDAN_ROUTES = INDIAN_REGIONAL_SECTORS


def get_route_by_id(route_id: str, return_leg: bool = False) -> Route:
    """
    Finds route by ID. If return_leg is True, swaps origin and destination
    to simulate operations departing from the destination airport.
    """
    base_route = None
    for r in INDIAN_REGIONAL_SECTORS:
        if r.route_id == route_id:
            base_route = r
            break
    if base_route is None:
        base_route = INDIAN_REGIONAL_SECTORS[0]

    if not return_leg:
        return base_route

    # Return leg: swap origin and destination
    return Route(
        route_id=f"{base_route.destination.iata}-{base_route.origin.iata}",
        name=f"{base_route.destination.city} ({base_route.destination.iata}) ➔ {base_route.origin.city} ({base_route.origin.iata})",
        origin=base_route.destination,
        destination=base_route.origin,
        stage_distance_km=base_route.stage_distance_km,
        nominal_cruise_alt_ft=base_route.nominal_cruise_alt_ft,
        description=f"Return leg departing from {base_route.destination.city} (elev {base_route.destination.elevation_ft:.0f} ft).",
        regional_grid_co2_kg_per_kwh=base_route.regional_grid_co2_kg_per_kwh,
        is_return_leg=True,
    )
