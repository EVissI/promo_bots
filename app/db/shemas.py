from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.db.models import ConnectedEntity, User,SavedMediaFile, ForwardedMessage

class ConnectedEntityModel(BaseModel):
    entity_id: int
    entity_type: ConnectedEntity.EntityType
    last_message_id: Optional[int]

class ConnectedEntityFilter(BaseModel):
    entity_id: int = None
    entity_type: ConnectedEntity.EntityType = None
    last_message_id: Optional[int] = None

class ForwardedMessageModel(BaseModel):
    entity_id: int
    message_id: int
    sent:bool 

class ForwardedMessageErrosModel(BaseModel):
    message_id:int
    error_text:str

class ForwardedMessageFilter(BaseModel):
    entity_id: int = None
    message_id: int = None
    sent:bool = None

class TelegramIDModel(BaseModel):
    telegram_id: int
    class Config:
        from_attributes = True

class UserModel(TelegramIDModel):
    username: Optional[str]
    first_name:Optional[str]
    promo_code: Optional[str] = None
    subscription_end: Optional[datetime] = None
    is_blocked:bool = False
    role:User.Role = User.Role.user

class UserFilterModel(BaseModel):
    telegram_id: int = None
    username: Optional[str] = None
    first_name:Optional[str] = None
    promo_code: Optional[str] = None
    subscription_end: Optional[datetime] = None
    subscription_end_gt: Optional[datetime] = None  # Greater 
    subscription_end_lt: Optional[datetime] = None  # Less 
    is_blocked:bool = None
    role:User.Role = None

class PromocodeModel(BaseModel):
    promo_name: str
    duration: int 
    usage_limit: int
    used_count: int 
    
class PromocodeFilter(BaseModel):
    promo_name: str = None
    duration: int = None
    usage_limit: int = None
    used_count: int = None

class SavedMediaFileModel(BaseModel):
    file_id:str
    file_media_type:SavedMediaFile.MediaTypes

class SavedMediaFileFilter(BaseModel):
    file_id:str = None
    file_media_type:SavedMediaFile.MediaTypes = None