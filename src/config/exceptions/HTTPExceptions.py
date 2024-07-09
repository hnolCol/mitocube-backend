from fastapi.exceptions import HTTPException
from fastapi import status

share_token_pw_incorrect = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate the share token password.",
        headers={"WWW-Authenticate": "Bearer"})

credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. User not found or password incorrect.",
        headers={"WWW-Authenticate": "Bearer"})


user_form_data_incorrect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or password incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

user_role_too_low = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The required user role is not matched.",
            headers={"WWW-Authenticate": "Bearer"},
        )

user_blocked = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User blocked and not allowed for login.",
            headers={"WWW-Authenticate": "Bearer"},
        )

user_forbidden = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The user doesnt have the required user role to perform this task.",
            headers={"WWW-Authenticate": "Bearer"},
        )

user_not_found = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user is not in the database.",
            headers={"WWW-Authenticate": "Bearer"},
        )

user_registration_failed = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The user registration failed. User mail might already be registered.",
            headers={"WWW-Authenticate": "Bearer"},
        )

verification_code_missing = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid. Verification not found.",
            headers={"WWW-Authenticate": "Bearer"})

verification_code_incorrect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verification failed. verification_code incorrect.",
            headers={"WWW-Authenticate": "Bearer"})

token_experied_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token expired. Please login again.",
        headers={"WWW-Authenticate": "Bearer"})

token_not_verified_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token not verified.",
        headers={"WWW-Authenticate": "Bearer"})

token_not_valid_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalid.",
        headers={"WWW-Authenticate": "Bearer"})


validation_code_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Validation code incorrect.",
        headers={"WWW-Authenticate": "Bearer"})


dataid_not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Dataset ID/Label was not found.",
        headers={"WWW-Authenticate": "Bearer"})

tag_not_found = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Label was not found.",
        headers={"WWW-Authenticate": "Bearer"})

no_data_found_http_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No datatable could be found for the label.",
        headers={"WWW-Authenticate": "Bearer"})

mandatory_dataset_attrs_not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Mandatory dataset attribute missing.",
        headers={"WWW-Authenticate": "Bearer"})


filter_tag_does_not_exist_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="The provided filter tag was not found in the DB.",
        headers={"WWW-Authenticate": "Bearer"})