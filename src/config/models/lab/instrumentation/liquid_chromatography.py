from pydantic import BaseModel

class LiquidChromatography(BaseModel):
    """Base Model for a Liquid Chromatography."""
    name : str
    company : str
    serial_number : str
    product_number : str 