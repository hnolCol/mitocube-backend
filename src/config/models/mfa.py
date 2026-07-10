
# config/models/mfa.py
from pydantic import BaseModel

class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str  # base64 data URI
    token : str  # token for enabling MFA

class MFAEnableRequest(BaseModel):
    code: str

class MFAStatusResponse(BaseModel):
    mfa_enabled: bool

class MFADisableRequest(BaseModel):
    password: str
    code: str