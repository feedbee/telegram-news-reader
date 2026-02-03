
import os
import logging
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Initialize Firebase Admin
service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json")

if not firebase_admin._apps:
    if os.path.exists(service_account_path):
        try:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin initialized with service account: {service_account_path}")
        except Exception as e:
            logger.critical(f"Failed to initialize Firebase Admin with service account: {e}")
            raise RuntimeError(f"Critical error: Firebase Admin SDK failed to initialize: {e}")
    else:
        logger.critical(f"Firebase service account file not found at: {service_account_path}")
        raise FileNotFoundError(f"Firebase service account JSON file is required: {service_account_path}")

security = HTTPBearer()

async def get_current_user(auth_creds: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifies the Firebase ID token using firebase-admin SDK.
    """
    token = auth_creds.credentials
    try:
        # verify_id_token() verifies the signature, expiration, and audience (project ID).
        # It throws exceptions if any check fails.
        decoded_token = auth.verify_id_token(token)
        
        user_id = decoded_token.get("uid")
        email = decoded_token.get("email")
        
        logger.info(f"Authenticated user: {email} ({user_id})")
        return {"uid": user_id, "email": email}
        
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token expired")
    except auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token revoked")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")
