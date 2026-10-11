from typing import Self
from pydantic import BaseModel, model_validator


class RegisterRequest(BaseModel):
    password: str
    confirm_password: str

    @model_validator(mode="after")
    def validate_passwords(self) -> Self:
        if self.password != self.confirm_password:
            raise ValueError("两次密码不一致")
        return self


request = RegisterRequest(
    password="abc123",
    confirm_password="abc456",
)  # 抛出 ValidationError
