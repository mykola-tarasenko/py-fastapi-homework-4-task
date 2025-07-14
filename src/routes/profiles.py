from fastapi import APIRouter, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_jwt_auth_manager, get_s3_storage_client
from schemas import ProfileResponseSchema, ProfileRequestSchema
from database import (
    get_db,
)
from security.interfaces import JWTAuthManagerInterface
from storages import S3StorageInterface

router = APIRouter()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.post(
    "/users/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def user_profile(
        data: ProfileRequestSchema,
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        s3_client: S3StorageInterface = Depends(get_s3_storage_client)
) -> ProfileResponseSchema:
    ...