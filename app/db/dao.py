from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import BaseDAO
from app.db.models import ForwardedMessageError, User,ConnectedEntity,ForwardedMessage,Promocode,SavedMediaFile
from app.db.shemas import UserFilterModel,ForwardedMessageFilter




class UserDAO(BaseDAO[User]):
    model = User
    async def get_admins(session:AsyncSession) -> list[User]|None:
        """
        Получает список всех администраторов.
        """
        filters = UserFilterModel(role=User.Role.admin)
        return await UserDAO.find_all(session, filters=filters)
    async def get_blocked_users(session:AsyncSession) -> list[User]|None:
        """
        Получает список всех заблокированных юзеров.
        """
        filters = UserFilterModel(is_blocked=True)
        return await UserDAO.find_all(session, filters=filters)
    

    @staticmethod
    async def find_all_non_banned_users(session, filters=None):
        query = select(User)
        if filters:
            if filters.is_blocked is not None:
                query = query.where(User.is_blocked == filters.is_blocked)
            if filters.subscription_end_gt:
                query = query.where(User.subscription_end > filters.subscription_end_gt)
            if filters.subscription_end_lt:
                query = query.where(User.subscription_end < filters.subscription_end_lt)
        result = await session.execute(query)
        return result.scalars().all()
    

class ConnectedEntityDAO(BaseDAO[ConnectedEntity]):
    model = ConnectedEntity

class ForwardedMessageDAO(BaseDAO[ForwardedMessage]):
    model = ForwardedMessage

    @classmethod
    async def get_not_sendings_messages(cls, session: AsyncSession, limit: int = None) -> list[ForwardedMessage]:
        """
        Получает список всех не отправленных сообщений, которых нет в таблице ForwardedMessageError.
        """
        query = (
            select(cls.model)
            .outerjoin(ForwardedMessageError, ForwardedMessage.id == ForwardedMessageError.message_id)
            .where(ForwardedMessage.sent == False)
            .where(ForwardedMessageError.id == None)
            .limit(limit)
        )
        result = await session.execute(query)
        return result.scalars().all()
    @classmethod
    async def get_max_message_id(cls, session: AsyncSession, entity_id: int) -> int|None:
        """
        Получаем максимальное значение id
        """
        query = select(func.max(cls.model.message_id)).where(
            cls.model.entity_id == entity_id
        )
        result = await session.execute(query)
        max_id = result.scalar()
        return max_id if max_id is not None else None

class ForwardedMessageErrorDAO(BaseDAO[ForwardedMessageError]):
    model = ForwardedMessageError

class PromocodeDAO(BaseDAO[Promocode]):
    model = Promocode

class SavedMediaFileDAO(BaseDAO[SavedMediaFile]):
    model = SavedMediaFile

