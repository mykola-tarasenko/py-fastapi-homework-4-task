from botocore.exceptions import (
    BotoCoreError,
    NoCredentialsError,
    HTTPClientError,
    ConnectionError,
)
from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


from config import get_jwt_auth_manager, get_s3_storage_client
from exceptions import TokenExpiredError
from schemas import ProfileResponseSchema, ProfileCreateSchema
from database import (
    get_db,
    UserModel,
    UserProfileModel,
)
from security.interfaces import JWTAuthManagerInterface
from storages import S3StorageInterface

router = APIRouter()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


@router.post(
    "/users/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def user_profile(
    user_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client),
    data: ProfileCreateSchema = Depends(ProfileCreateSchema.from_form),
) -> ProfileResponseSchema:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )

    try:
        decoded_token = jwt_manager.decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
        )
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired."
        )

    if decoded_token["user_id"] != user_id or not decoded_token.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this profile.",
        )

    db_user_stmt = select(UserModel).where(UserModel.id == user_id)
    db_user_result = await db.execute(db_user_stmt)
    db_user = db_user_result.scalar_one_or_none()

    if not db_user or not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active.",
        )

    db_user_profile_stmt = select(UserProfileModel).where(
        UserProfileModel.user_id == user_id
    )
    db_user_profile_result = await db.execute(db_user_profile_stmt)
    db_user_profile = db_user_profile_result.scalar_one_or_none()

    if db_user_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile.",
        )

    try:
        filename = f"avatars/{user_id}_avatar.jpg"
        await s3_client.upload_file(filename, await data.avatar.read())

        new_user_profile = UserProfileModel(
            first_name=data.first_name.lower(),
            last_name=data.last_name.lower(),
            avatar=filename,
            gender=data.gender,
            date_of_birth=data.date_of_birth,
            info=data.info,
            user_id=user_id,
        )
        db.add(new_user_profile)

        await db.commit()
        await db.refresh(new_user_profile)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create a profile.",
        )
    except (ConnectionError, HTTPClientError, NoCredentialsError, BotoCoreError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later.",
        )
    else:
        return ProfileResponseSchema(
            id=new_user_profile.id,
            user_id=new_user_profile.user_id,
            first_name=new_user_profile.first_name,
            last_name=new_user_profile.last_name,
            gender=new_user_profile.gender,
            date_of_birth=new_user_profile.date_of_birth,
            info=new_user_profile.info,
            avatar=await s3_client.get_file_url(filename),
        )
