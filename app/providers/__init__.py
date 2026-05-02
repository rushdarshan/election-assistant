from app.providers.base import JurisdictionProvider
from app.providers.us_provider import USProvider
from app.providers.india_provider import IndiaProvider

def get_provider(country: str) -> JurisdictionProvider:
    if country.upper() == "US":
        return USProvider()
    elif country.upper() == "IN":
        return IndiaProvider()
    else:
        raise ValueError(f"Unsupported country: {country}")
