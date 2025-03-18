from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandObject, Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.aiogram.common.messages import get_text
from app.aiogram.common.states import ChangePassStates
from app.aiogram.filters.get_user_info import GetUserInfoFilter
from app.aiogram.keyboards.markup_kb import MainKeyboard
from app.db.dao import UserDAO, PromocodeDAO, AdminLoginDAO
from app.db.database import connection
from app.db.models import User
from app.db.shemas import TelegramIDModel, PromocodeFilter, AdminLoginFilter
from app.config import bot

admin_router = Router()


@admin_router.message(Command("send_promo"), GetUserInfoFilter())
@connection()
async def cmd_send_promo(
    message: Message, command: CommandObject, user_info: User, session, **kwargs
):
    try:
        if command.args is None:
            await message.answer(
                get_text("error_no_arguments_passed", lang=user_info.language_code)
            )
            return

        try:
            user_id, promo_name = command.args.split(" ", maxsplit=1)
        except ValueError:
            await message.answer(
                get_text("error_wrong_promo_args", lang=user_info.language_code)
            )
            return

        user = await UserDAO.find_one_or_none(
            session, TelegramIDModel(telegram_id=user_id)
        )
        if not user:
            await message.answer(
                get_text("error_user_not_found", lang=user_info.language_code)
            )
            return
        promo = await PromocodeDAO.find_one_or_none(
            session, PromocodeFilter(promo_name=promo_name)
        )
        if not promo:
            await message.answer(
                get_text("error_promo_not_found", lang=user_info.language_code)
            )
            return
        await bot.send_message(
            user.telegram_id,
            get_text(
                "promo_message",
                lang=user.language_code,
                promo_code=promo.promo_name,
                activate_button=MainKeyboard.get_user_kb_texts(user.language_code).get(
                    "activate_promo"
                ),
            ),
        )
    except Exception as e:
        logger.error(
            f"При отсылке промокода произошла командой /send_promo произошла ошибка: {str(e)}"
        )
        await message.answer(get_text("error_occurred", lang=user_info.language_code))


@admin_router.message(
    F.text.in_(
        [
            MainKeyboard.get_admin_kb_texts("ru").get(
                "change_password_for_flask_admin"
            ),
            MainKeyboard.get_admin_kb_texts("ru").get(
                "change_password_for_flask_admin"
            ),
        ]
    ),
    GetUserInfoFilter(),
)
async def cmd_change_pass_for_flask_admin(
    message: Message, state: FSMContext, user_info: User
):
    await message.answer(get_text("insert_new_pass", user_info.language_code))
    await state.set_state(ChangePassStates.waiting_pass)


@admin_router.message(F.text, ChangePassStates.waiting_pass,GetUserInfoFilter())
@connection()
async def change_admin_pass(message: Message, state: FSMContext,user_info:User, session, **kwargs):
    acc = await AdminLoginDAO.find_one_or_none(
        session, AdminLoginFilter()
    )
    if acc:
        await AdminLoginDAO.update(
            session, AdminLoginFilter(login='admin'), AdminLoginFilter(password=message.text)
        )
    else:
        await AdminLoginDAO.add(
            session, AdminLoginFilter(login='admin',password=message.text)
        )
    await state.clear()
    await message.answer(get_text("change_pass_successful", user_info.language_code))
