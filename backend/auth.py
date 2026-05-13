from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from config import settings

security = HTTPBasic()

def verify_dashboard_auth(credentials: HTTPBasicCredentials = Depends(security)):
    # Accept any username (or empty username) with correct password
    correct_password = credentials.password == settings.DASHBOARD_PASSWORD
    if not correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiges Passwort",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True
