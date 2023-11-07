from fastapi import Depends, status
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer

from jose import JWTError, jwt, ExpiredSignatureError

from passlib.context import CryptContext

from typing import List
from datetime import datetime 

from config.settings.encryption import Encryption
from config.settings.token import get_user_token_settings, get_share_token_settings
from config.exceptions.HTTPExceptions import credentials_exception, verification_code_missing
from services.date import get_current_datetime

#load encryption settings
encryption_settings = Encryption()
user_token_settings = get_user_token_settings()
SHARE_TOKEN_SETTINGS = get_share_token_settings()
pwd_context = CryptContext(schemes=[encryption_settings.hash_algorithm], 
                           deprecated="auto")
#scheme to validate token 
oauth2_scheme_validate = OAuth2PasswordBearer(tokenUrl="api/auth/token/verify", auto_error=False)
#scheme to create token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="", auto_error=False)
#scheme to create share token
oauth2_scheme_share = OAuth2PasswordBearer(tokenUrl="api/auth/token/share", auto_error=False)
#oauth2_scheme_user = OAuth2PasswordBearer(tokenUrl="api/user", auto_error=False)


def create_password_hash(password : str) -> str:
    """Create a passsword hash using the pwd-cryp. Salt is automatically generated.

    Documentation
    https://passlib.readthedocs.io/en/stable/lib/passlib.hash.bcrypt.html#passlib.hash.bcrypt
    """
    return pwd_context.hash(password)

def verify_password(plain_password : str, password_hash : str) -> bool:
    """Verifies a given plain password against a password hash"""
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(data: dict, 
                        key_subset : List[str] = None, 
                        add_dict : dict = None, share_token : bool = False) -> str:
    """
    Encodes data (dict) in a jwt token using the jwt secret key.

    :key_subset ```List[str]```: Specifies key in data that should be used.
    :add_dict ```Dict```: A dict that can be added to the data. 
    
    Returns 
    jwt token as a string
    """
    
    if len(data) == 0:
        raise ValueError("Empty dict passed to create jwt token.")
    
    if key_subset is None:
        
        to_encode = data.copy()

    else:
        if not any(k in data for k in key_subset):

            raise ValueError("Not a single key of key_subset is present in data.")
        
        to_encode = dict([(k,v) for k,v in data.items() if k in key_subset])
    
    if add_dict is not None and isinstance(add_dict,dict):
        for k,v in add_dict.items():
            to_encode[k] = v
    current_time = get_current_datetime()
    if share_token:
        return create_share_token(to_encode, current_time)
    else:
        
        expire = current_time + user_token_settings.expires_after_hours

        to_encode["exp"] = expire

        return jwt.encode(to_encode,
                        user_token_settings.jwt_key.get_secret_value(), 
                        algorithm=user_token_settings.jwt_algorithm)

def create_share_token(to_encode : dict, current_time : datetime) -> str:
    """
    Create a share token.
    """
    
    expire = current_time + SHARE_TOKEN_SETTINGS.expires_after_hours

    to_encode["exp"] = expire
    return jwt.encode(to_encode,
                    SHARE_TOKEN_SETTINGS.jwt_share_key.get_secret_value(), 
                    algorithm=SHARE_TOKEN_SETTINGS.jwt_algorithm)

def get_decoded_token(token : str = Depends(oauth2_scheme)):
    "Decodes token from HTTP request"
    print(token,"cannot find tokne?")
    return decode_token(token)

def get_decoded_token_for_verification(token = Depends(oauth2_scheme_validate)):
    "Decodes token from HTTP request"
    return decode_token(token)

def get_decoded_share_token(token : str = Depends(oauth2_scheme_share)):
    """Decodes token from HTTP request for sharing qc data"""
    return decode_token(token)

def decode_token(token : str) -> dict:
    """Decode jwt token"""
    try:
        token_data = jwt.decode(token, user_token_settings.jwt_key.get_secret_value(), 
                                algorithms=[user_token_settings.jwt_algorithm])
    except ExpiredSignatureError:
        #move expections to HTTP Exceptions
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"})
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not valid.",
            headers={"WWW-Authenticate": "Bearer"})
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not valid.",
            headers={"WWW-Authenticate": "Bearer"})
    return token_data


def check_for_verification_code_in_token(decoded_token = Depends(get_decoded_token_for_verification)) -> str:
    """
    Checks if decoded token contains the verification code.
    Function Depends on get_decoded_token. 
    Exceptions
        HTTP Exception (Token invalid, Verification not found).
    Returns
    decoded token 
    """
    if "verification_code" not in decoded_token:
        raise verification_code_missing
    return decoded_token



def check_share_token_password(plainPassword : str) -> bool:
    """Checks if the share token password is correct."""
    return SHARE_TOKEN_SETTINGS.share_token_pw.get_secret_value() == plainPassword
   
    
