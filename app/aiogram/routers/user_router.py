from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
from loguru import logger
from app.aiogram.common.states import ActivatePromoState, PaymentStates
from app.aiogram.filters.get_user_info import GetUserInfoFilter
from app.aiogram.keyboards.inline_kb import ChangeLanguage, change_lang_kb, oplata_kb
from app.aiogram.keyboards.markup_kb import MainKeyboard, del_kbd
from aiogram.filters import StateFilter, Command, CommandObject
from aiogram.fsm.context import FSMContext
from app.db.dao import UserDAO, PromocodeDAO, Promocode, User
from app.db.database import async_session_maker
from app.db.shemas import PromocodeFilter, TelegramIDModel, UserModel, PromocodeModel
from app.config import bot, admins, settings
from app.aiogram.common.messages import get_text

user_router = Router()


@user_router.message(
    F.text.in_(
        [
            MainKeyboard.get_user_kb_texts("ru").get("activate_promo"),
            MainKeyboard.get_user_kb_texts("en").get("activate_promo"),
        ]
    )
)
async def cmd_activate_promo(message: Message, state: FSMContext):
    await message.answer("Введите промокод", reply_markup=del_kbd)
    await state.set_state(ActivatePromoState.promo)


@user_router.message(StateFilter(ActivatePromoState.promo), F.text)
async def process_activate_promo(message: Message, state: FSMContext):
    try:
        async with async_session_maker() as session:
            promo_info: Promocode = await PromocodeDAO.find_one_or_none(
                session=session, filters=PromocodeFilter(promo_name=message.text)
            )
            user_info: User = await UserDAO.find_one_or_none(
                session=session,
                filters=TelegramIDModel(telegram_id=message.from_user.id),
            )
        logger.info(user_info)
        if not promo_info:
            await message.answer(
                get_text("promocode_is_not_found", lang=user_info.language_code),
                reply_markup=MainKeyboard.build_main_kb(
                    user_info.role, user_info.language_code
                ),
            )
            await state.clear()
            return

        if user_info.promo_code == promo_info.promo_name:
            await message.answer(
                get_text("promocode_is_was_used", lang=user_info.language_code),
                reply_markup=MainKeyboard.build_main_kb(
                    user_info.role, user_info.language_code
                ),
            )
            await state.clear()
            return

        promo_info.used_count += 1
        user_info.promo_code = promo_info.promo_name

        current_date = datetime.now()
        end_date = current_date + timedelta(days=promo_info.duration)
        user_info.subscription_end = end_date
        async with async_session_maker() as session:
            if promo_info.used_count == promo_info.usage_limit:
                await PromocodeDAO.delete(
                    session=session,
                    filters=PromocodeFilter(promo_name=promo_info.promo_name),
                )
            else:
                await PromocodeDAO.update(
                    session=session,
                    filters=PromocodeFilter(promo_name=promo_info.promo_name),
                    values=PromocodeModel.model_validate(promo_info.to_dict()),
                )
        async with async_session_maker() as session:
            await UserDAO.update(
                session=session,
                filters=TelegramIDModel(telegram_id=message.from_user.id),
                values=UserModel.model_validate(user_info.to_dict()),
            )
        await message.answer(
            get_text(
                "promocode_used_successfully",
                lang=user_info.language_code,
                end_date=end_date.date(),
            ),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )
        await state.clear()
        for admin in admins:
            try:
                msg = (
                    f"пользователь {user_info.first_name}(username: @{user_info.username}, id: {user_info.telegram_id})"
                    if user_info.username
                    else f"пользователь {user_info.first_name}(id: {user_info.telegram_id})"
                )
                await bot.send_message(
                    admin, msg + f" зарегистрировал промокод {promo_info.promo_name}"
                )
            except TelegramNotFound:
                logger.error(
                    f"Рутовский администратор[{admin}] не найдет, скоректир скорректируйте .env файл"
                )
    except TelegramForbiddenError:
        pass
    except Exception as e:
        logger.error(
            f"Ошибка при активации промокода юзером {message.from_user.first_name} [{message.from_user.id}] : {str(e)}"
        )
        await message.answer(
            get_text("error_somthing_went_wrong", lang=message.from_user.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )
        await state.clear()


@user_router.message(
    F.text.in_(
        [
            MainKeyboard.get_user_kb_texts("ru").get("check_sub"),
            MainKeyboard.get_user_kb_texts("en").get("check_sub"),
        ]
    )
)
async def check_subscription(message: Message, state: FSMContext):
    try:
        async with async_session_maker() as session:
            user_info = await UserDAO.find_one_or_none(
                session=session,
                filters=TelegramIDModel(telegram_id=message.from_user.id),
            )

            if not user_info.subscription_end:
                await message.answer(
                    get_text("have_no_sub", lang=user_info.language_code),
                    reply_markup=MainKeyboard.build_main_kb(
                        user_info.role, user_info.language_code
                    ),
                )
                return

            current_date = datetime.now()
            days_left = (user_info.subscription_end - current_date).days

            if days_left < 0:
                await message.answer(
                    get_text("sub_is_end", lang=user_info.language_code),
                    reply_markup=MainKeyboard.build_main_kb(
                        user_info.role, user_info.language_code
                    ),
                )
            else:
                await message.answer(
                    get_text(
                        "sub_is_active",
                        lang=user_info.language_code,
                        days_left=days_left,
                        end_date=user_info.subscription_end.date(),
                    ),
                    reply_markup=MainKeyboard.build_main_kb(
                        user_info.role, user_info.language_code
                    ),
                )

    except Exception as e:
        logger.error(
            f"Ошибка при проверке подписки пользователем {message.from_user.first_name} [{message.from_user.id}]: {str(e)}"
        )
        await message.answer(
            get_text("error_somthing_went_wrong", lang=message.from_user.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )


@user_router.message(
    F.text.in_(
        [
            MainKeyboard.get_user_kb_texts("ru").get("oplata"),
            MainKeyboard.get_user_kb_texts("en").get("oplata"),
        ]
    ),
    GetUserInfoFilter(),
)
async def process_payment(message: Message, state: FSMContext, user_info: User):
    try:
        await message.answer(
            get_text(
                "payment_form",
                user_info.language_code,
                phone_number="+7 999 999 99 99",
                payment_amount="2000",
            ),
            reply_markup=oplata_kb(),
        )
        await state.set_state(PaymentStates.waiting_for_payment)
    except Exception as e:
        logger.error(f"Ошибка при запросе оплаты: {e}")
        await message.answer(
            get_text("error_somthing_went_wrong", user_info.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )


@user_router.callback_query(F.data == "payment_done", GetUserInfoFilter())
async def payment_confirmation(
    callback: CallbackQuery, state: FSMContext, user_info: User
):
    try:
        await callback.message.delete()
        await callback.message.answer(
            get_text("payment_check_pls", lang=user_info.language_code)
        )
        await state.set_state(PaymentStates.waiting_for_screenshot)
    except Exception as e:
        logger.error(f"Ошибка при подтверждении оплаты: {e}")
        await callback.message.answer(
            get_text("error_somthing_went_wrong", user_info.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )


@user_router.message(PaymentStates.waiting_for_screenshot, F.photo, GetUserInfoFilter())
async def process_payment_screenshot(
    message: Message, state: FSMContext, user_info: User
):
    try:
        await bot.send_photo(
            settings.ADMIN_GROUP_ID,
            message.photo[-1].file_id,
            caption=f"Новая оплата от пользователя {message.from_user.first_name} (ID: <code>{message.from_user.id}</code>)",
        )
        await message.answer(
            get_text("ty_yr_payment_was_successfully", lang=user_info.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обработке скриншота: {e}")
        await message.answer(
            get_text("error_somthing_went_wrong", user_info.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )


@user_router.message(Command("activate_promo"), GetUserInfoFilter())
async def cmd_activate_promo(message: Message, command: CommandObject, user_info: User):
    try:
        if command.args is None:
            await message.answer(
                get_text("error_promo_args", lang=user_info.language_code)
            )
            return
        if command.args.count(" ") > 1:
            await message.answer("Ошибка: слишком много аргументов")
            return
        promo = command.args

        async with async_session_maker() as session:
            promo_info: Promocode = await PromocodeDAO.find_one_or_none(
                session=session, filters=PromocodeFilter(promo_name=promo)
            )
            if promo_info is None:
                await message.answer(
                    get_text("promocode_is_not_found", lang=user_info.language_code),
                )
                return
            if promo_info.promo_name == user_info.promo_code:
                await message.answer(
                    get_text("promocode_is_was_used", lang=user_info.language_code),
                )
                return
        promo_info.used_count += 1
        user_info.promo_code = promo_info.promo_name

        current_date = datetime.now()
        end_date = current_date + timedelta(days=promo_info.duration)
        user_info.subscription_end = end_date
        async with async_session_maker() as session:
            if promo_info.used_count == promo_info.usage_limit:
                await PromocodeDAO.delete(
                    session=session,
                    filters=PromocodeFilter(promo_name=promo_info.promo_name),
                )
            else:
                await PromocodeDAO.update(
                    session=session,
                    filters=PromocodeFilter(promo_name=promo_info.promo_name),
                    values=PromocodeModel.model_validate(promo_info.to_dict()),
                )
        async with async_session_maker() as session:
            await UserDAO.update(
                session=session,
                filters=TelegramIDModel(telegram_id=message.from_user.id),
                values=UserModel.model_validate(user_info.to_dict()),
            )
        await message.answer(
            get_text(
                "promocode_used_successfully",
                lang=user_info.language_code,
                end_date=end_date.date(),
            ),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при активации промкода коммандой: {e}")
        await message.answer(
            get_text("error_somthing_went_wrong", user_info.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )


@user_router.message(
    F.text.in_(
        [
            MainKeyboard.get_user_kb_texts("ru").get("change_lang"),
            MainKeyboard.get_user_kb_texts("en").get("change_lang"),
        ]
    ),
    GetUserInfoFilter(),
)
async def change_language(message: Message, user_info: User):
    try:
        await message.answer(
            get_text("change_language", lang=user_info.language_code),
            reply_markup=change_lang_kb(),
        )
    except Exception as e:
        logger.error(f"Ошибка при смене языка: {e}")
        await message.answer(
            get_text("error_somthing_went_wrong", lang=user_info.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )


@user_router.callback_query(ChangeLanguage.filter(), GetUserInfoFilter())
async def change_language_callback(
    query: CallbackQuery, callback_data: ChangeLanguage, user_info: User
):
    try:
        await query.message.delete()
        user_info.language_code = callback_data.lang
        async with async_session_maker() as session:
            await UserDAO.update(
                session=session,
                filters=TelegramIDModel(telegram_id=user_info.telegram_id),
                values=UserModel.model_validate(user_info.to_dict()),
            )
        await query.message.answer(
            get_text("language_changed", lang=user_info.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при смене языка: {e}")
        await query.message.answer(
            get_text("error_somthing_went_wrong", lang=user_info.language_code),
            reply_markup=MainKeyboard.build_main_kb(
                user_info.role, user_info.language_code
            ),
        )
