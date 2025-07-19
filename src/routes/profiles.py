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
from exceptions import TokenExpiredError, S3FileUploadError
from schemas import ProfileResponseSchema, ProfileCreateSchema
from database import (
    get_db,
    UserModel,
    UserProfileModel,
    UserGroupModel,
    UserGroupEnum,
)
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface
from storages import S3StorageInterface

router = APIRouter()


@router.post(
    "/users/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def user_profile(
    user_id: int,
    token: str = Depends(get_token),
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client),
    data: ProfileCreateSchema = Depends(ProfileCreateSchema.from_form),
) -> ProfileResponseSchema:
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

    current_user_id = decoded_token["user_id"]

    if current_user_id != user_id:
        group_stmt = (
            select(UserGroupModel)
            .join(UserModel)
            .where(UserModel.id == current_user_id)
        )
        group_result = await db.execute(group_stmt)
        user_group = group_result.scalars().first()
        if not user_group or user_group.name == UserGroupEnum.USER:
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

    avatar_data = await data.avatar.read()
    avatar_key = f"avatars/{user_id}_{data.avatar.filename}"

    try:
        await s3_client.upload_file(file_name=avatar_key, file_data=avatar_data)
    except S3FileUploadError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later.",
        )

    new_user_profile = UserProfileModel(
        first_name=data.first_name.lower(),
        last_name=data.last_name.lower(),
        avatar=avatar_key,
        gender=data.gender,
        date_of_birth=data.date_of_birth,
        info=data.info,
        user_id=user_id,
    )

    db.add(new_user_profile)
    await db.commit()
    await db.refresh(new_user_profile)

    return ProfileResponseSchema(
        id=new_user_profile.id,
        user_id=new_user_profile.user_id,
        first_name=new_user_profile.first_name,
        last_name=new_user_profile.last_name,
        gender=new_user_profile.gender,
        date_of_birth=new_user_profile.date_of_birth,
        info=new_user_profile.info,
        avatar=await s3_client.get_file_url(avatar_key),
    )
