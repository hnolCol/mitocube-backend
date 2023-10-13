from pydantic import BaseModel

class MassSpectrometer(BaseModel):
    """Base Model for a Mass Spectrometer."""
    name : str
    company : str
    serial_number : str
    product_number : str = ""
    description : str = ""