from datetime import date

from fastapi import UploadFile, Form, File, HTTPException
from pydantic import BaseModel, field_validator, HttpUrl

from validation import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date
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


class ProfileRequestSchema(BaseModel):
    id: id = Form()
    user_id: int = Form()
    first_name: str = Form()
    last_name: str = Form()
    gender: str = Form()
    date_of_birth: date = Form()
    info: str = Form()
    avatar: UploadFile

    @field_validator("name")
    def validate_name(self, name: str):
        return validate_name(name)

    @field_validator("image")
    def validate_image(self, image: UploadFile):
        return validate_image(image)

    @field_validator("gender")
    def validate_gender(self, gender: str):
        return validate_gender(gender)

    @field_validator("birth_date")
    def validate_birth_date(self, birth_date: date):
        return validate_birth_date(birth_date)