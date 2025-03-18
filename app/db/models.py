import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, DateTime,Boolean, Enum, ForeignKey, Integer,String
from typing import Optional
from app.db.database import Base


class User(Base):
    class Role(enum.Enum):
        admin = "admin"
        user = "user"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String, default=None)
    first_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    promo_code: Mapped[str] = mapped_column(String, default=None,nullable=True)
    subscription_end : Mapped[DateTime] = mapped_column(DateTime, default=None,nullable=True)
    is_blocked:Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.user)
    language_code: Mapped[str] = mapped_column(String, default='ru')

class ConnectedEntity(Base):
    class EntityType(enum.Enum):
        channel = 'channel'
        group = 'group'
    entity_id: Mapped[int] = mapped_column(BigInteger, default=None)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), default=None)
    last_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

class ForwardedMessage(Base):
    entity_id: Mapped[int] = mapped_column(BigInteger, default=None)
    message_id: Mapped[int] = mapped_column(BigInteger, default=None)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)

    error:Mapped['ForwardedMessageError'] = relationship("ForwardedMessageError",back_populates="forwarded_messages")

class ForwardedMessageError(Base):
    message_id:Mapped[int]= mapped_column(Integer, ForeignKey('forwarded_messages.id'),unique=True)
    error_text: Mapped[str]
    
    forwarded_messages:Mapped['ForwardedMessage'] = relationship("ForwardedMessage",back_populates="error")

class Promocode(Base):
    promo_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    duration: Mapped[int] 
    usage_limit: Mapped[int]
    used_count: Mapped[int]= mapped_column(BigInteger, default=0)

class SavedMediaFile(Base):
    class MediaTypes(enum.Enum):
        photo = 'photo'
        video = 'video'
        video_note ="video_note"
    file_id: Mapped[str] = mapped_column(nullable=False)
    file_media_type: Mapped[MediaTypes] = mapped_column(Enum(MediaTypes), nullable=False)

class AdminLogin(Base):
    login: Mapped[str]
    password: Mapped[str]