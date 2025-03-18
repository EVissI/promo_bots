from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from loguru import logger
from app.aiogram.common.messages import get_text
from app.aiogram.keyboards.markup_kb import MainKeyboard
from app.aiogram.middlewarres.is_admin import CheckIsAdmin
from app.aiogram.middlewarres.is_banned import CheckIsBanned
from app.db.dao import UserDAO
from app.db.database import async_session_maker
from app.db.models import User
from app.db.shemas import TelegramIDModel, UserModel
from app.aiogram.routers.user_router import user_router
from app.aiogram.routers.receiving_messages import receiving_message_router
from app.aiogram.routers.admin import admin_router
from app.config import admins, bot

user_router.message.middleware(CheckIsBanned())
receiving_message_router.message.middleware(CheckIsAdmin())
admin_router.message.middleware(CheckIsAdmin())

main_router = Router()
main_router.include_router(user_router)
main_router.include_router(receiving_message_router)
main_router.include_router(admin_router)


@main_router.message(CommandStart())
async def cmd_start(message: Message):
    try:
        user_id = message.from_user.id
        async with async_session_maker() as session:
            user_info = await UserDAO.find_one_or_none(
                session=session, filters=TelegramIDModel(telegram_id=user_id)
            )
        if user_info:
            msg = get_text('start_msg', lang=user_info.language_code)
            if user_info.is_blocked == True:
                async with async_session_maker() as session:
                    user_info.is_blocked = False
                    await UserDAO.update(
                        session=session,
                        filters=TelegramIDModel(telegram_id=user_id),
                        values=UserModel.model_validate(user_info.to_dict()),
                    )
            await message.answer(msg, reply_markup=MainKeyboard.build_main_kb(user_info.role,user_info.language_code))
            return
        if user_id in admins:
            values = UserModel(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                promo_code=None,
                subscription_end=None,
                is_blocked=False,
                role=User.Role.admin,
                language_code=message.from_user.language_code
            )
            async with async_session_maker() as session:
                await UserDAO.add(session=session, values=values)
            await message.answer(
                "Привет администрации", reply_markup=MainKeyboard.build_main_kb(values.role,values.language_code)
            )
            return
        values = UserModel(
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            promo_code=None,
            subscription_end=None,
            is_blocked=False,
            role=User.Role.user,
            language_code=message.from_user.language_code
        )
        async with async_session_maker() as session:
            await UserDAO.add(session=session, values=values)
        msg = get_text('start_msg', lang=message.from_user.language_code)
        await message.answer(msg, reply_markup=MainKeyboard.build_main_kb(values.role,values.language_code))
        for admin in admins:
            await bot.send_message(
                admin,
                f"К тебе зашел новый юзер {message.from_user.first_name} [id: {message.from_user.id}]",
            )

    except Exception as e:
        logger.error(
            f"Ошибка при выполнении команды /start для пользователя {message.from_user.id}: {e}"
        )
        await message.answer(
            get_text('error_somthing_went_wrong', lang=message.from_user.language_code)
        )
