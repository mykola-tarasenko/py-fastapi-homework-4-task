from datetime import date

from fastapi import UploadFile, Form, File, HTTPException
from pydantic import BaseModel, field_validator, HttpUrl

from validation import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date,
)


class ProfileResponseSchema(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    info: str
    avatar: HttpUrl

    model_config = {"from_attributes": True}


class ProfileCreateSchema(BaseModel):
    first_name: str = Form(...)
    last_name: str = Form(...)
    gender: str = Form(...)
    date_of_birth: date = Form(...)
    info: str = Form(...)
    avatar: UploadFile = File(...)

    @classmethod
    def from_form(
        cls,
        first_name: str = Form(...),
        last_name: str = Form(...),
        gender: str = Form(...),
        date_of_birth: date = Form(...),
        info: str = Form(...),
        avatar: UploadFile = File(...),
    ) -> "ProfileCreateSchema":
        return cls(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar,
        )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, name: str):
        validate_name(name)
        return name

    @field_validator("avatar")
    @classmethod
    def validate_image(cls, image: UploadFile):
        validate_image(image)
        return image

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, gender: str):
        validate_gender(gender)
        return gender

    @field_validator("date_of_birth")
    @classmethod
    def validate_birth_date(cls, birth_date: date):
        validate_birth_date(birth_date)
        return birth_date
