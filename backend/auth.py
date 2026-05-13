from fastapi import HTTPException, status, Request
from config import settings
import base64

def verify_dashboard_auth(request: Request):
    """Prüfe Basic Auth manuell - ohne HTTPBasic() Dependency"""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passwort erforderlich"
        )

    try:
        # Decode: "Basic base64(username:password)" -> "username:password"
        encoded = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode('utf-8')
        username, password = decoded.split(":", 1)

        # Prüfe Passwort
        if password != settings.DASHBOARD_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Passwort ungültig"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentifizierung erforderlich"
        )

    return True
