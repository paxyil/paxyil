from pydantic import BaseModel


class CreateApplicationResponse(BaseModel):
    ok: bool
    application_id: int


class MessageResponse(BaseModel):
    ok: bool


class StatusResponse(BaseModel):
    ok: bool