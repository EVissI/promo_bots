import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message,CallbackQuery
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
from loguru import logger
from app.aiogram.common.states import ActivatePromoState,PaymentStates
from app.aiogram.keyboards.inline_kb import oplata_kb
from app.aiogram.keyboards.markup_kb import MainKeyboard, del_kbd
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from app.db.dao import UserDAO, PromocodeDAO, Promocode, User
from app.db.database import async_session_maker
from app.db.shemas import PromocodeFilter, TelegramIDModel, UserModel,PromocodeModel
from app.config import bot, admins, settings

user_router = Router()


@user_router.message(F.text == MainKeyboard.get_user_kb_texts().get("activate_promo"))
async def cmd_activate_promo(message: Message, state: FSMContext):
    await message.answer("Введите промокод", reply_markup=del_kbd)
    await state.set_state(ActivatePromoState.promo)


@user_router.message(StateFilter(ActivatePromoState.promo), F.text)
async def process_activate_promo(
    message: Message, state: FSMContext
):
    try:
        async with async_session_maker() as session:
            all_promocodes: list[Promocode] = await PromocodeDAO.find_all(
                session=session, filters=PromocodeFilter()
            )
            user_info: User = await UserDAO.find_one_or_none(
                session=session, filters=TelegramIDModel(telegram_id=message.from_user.id)
            )
        logger.info(user_info)
        user_input_promocode = message.text
        aproved_promo = None
        for promo in all_promocodes:
            if user_input_promocode != promo.promo_name:
                continue
            elif user_info.promo_code == message.text:
                await message.answer(
                    "Вы уже использовали этот промокод",
                    reply_markup=MainKeyboard.build_main_kb(),
                )
                await state.clear()
                return
            aproved_promo = promo

        if not aproved_promo:
            await message.answer('Промокода не существует',reply_markup=MainKeyboard.build_main_kb())
            await state.clear()
            return
        
        
        aproved_promo.used_count += 1
        user_info.promo_code = aproved_promo.promo_name

        current_date = datetime.now()
        end_date = current_date + timedelta(days=aproved_promo.duration)
        user_info.subscription_end = end_date
        async with async_session_maker() as session:
            if aproved_promo.used_count == aproved_promo.usage_limit:
                await PromocodeDAO.delete(
                    session=session,
                    filters=PromocodeFilter(promo_name=aproved_promo.promo_name),
                )
            else:
                await PromocodeDAO.update(
                    session=session,
                    filters=PromocodeFilter(promo_name=aproved_promo.promo_name),
                    values=PromocodeModel.model_validate(aproved_promo.to_dict()),
                )
        async with async_session_maker() as session:
            await UserDAO.update(
                session=session,
                filters=TelegramIDModel(telegram_id=message.from_user.id),
                values= UserModel.model_validate(user_info.to_dict())
            )
        await message.answer(
            f"Промокод успешно активирован, подписка кончится: {end_date.date()}",reply_markup= MainKeyboard.build_main_kb()
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
                    admin, msg + f' зарегистрировал промокод {aproved_promo.promo_name}'
                )
            except TelegramNotFound:
                logger.error(f'Рутовский администратор[{admin}] не найдет, скоректир скорректируйте .env файл')
    except TelegramForbiddenError:
        pass
    except Exception as e: 
        logger.error(f'Ошибка при активации промокода юзером {message.from_user.first_name} [{message.from_user.id}] : {str(e)}')
        await message.answer('Что-то пошло не так',reply_markup=MainKeyboard.build_main_kb())
        await state.clear()


@user_router.message(F.text == MainKeyboard.get_user_kb_texts().get('check_sub'))
async def check_subscription(message: Message, state: FSMContext):
    try:
        async with async_session_maker() as session:
            user_info = await UserDAO.find_one_or_none(
                session=session, 
                filters=TelegramIDModel(telegram_id=message.from_user.id)
            )
            
            if not user_info.subscription_end:
                await message.answer(
                    "У вас нет активной подписки", 
                    reply_markup=MainKeyboard.build_main_kb()
                )
                return
                
            current_date = datetime.now()
            days_left = (user_info.subscription_end - current_date).days
            
            if days_left < 0:
                await message.answer(
                    "Ваша подписка истекла", 
                    reply_markup=MainKeyboard.build_main_kb()
                )
            else:
                await message.answer(
                    f"Ваша подписка активна еще {days_left} дней\n"
                    f"Дата окончания: {user_info.subscription_end.date()}",
                    reply_markup=MainKeyboard.build_main_kb()
                )
                
    except Exception as e:
        logger.error(f'Ошибка при проверке подписки пользователем {message.from_user.first_name} [{message.from_user.id}]: {str(e)}')
        await message.answer('Что-то пошло не так', reply_markup=MainKeyboard.build_main_kb())

@user_router.message(F.text == MainKeyboard.get_user_kb_texts().get('oplata'))
async def process_payment(message: Message, state: FSMContext):
    try:
        await message.answer(
            f"Для оплаты переведите по номеру {settings.PAYMENT_NUMBER} - {settings.PAYMENT_AMOUNT}₽",
            reply_markup=oplata_kb()
        )
        await state.set_state(PaymentStates.waiting_for_payment)
    except Exception as e:
        logger.error(f'Ошибка при запросе оплаты: {e}')
        await message.answer('Что-то пошло не так', reply_markup=MainKeyboard.build_main_kb())

@user_router.callback_query(F.data == "payment_done")
async def payment_confirmation(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
        await callback.message.answer("Пришлите, пожалуйста, скриншот чека")
        await state.set_state(PaymentStates.waiting_for_screenshot)
    except Exception as e:
        logger.error(f'Ошибка при подтверждении оплаты: {e}')
        await callback.message.answer('Что-то пошло не так', reply_markup=MainKeyboard.build_main_kb())

@user_router.message(PaymentStates.waiting_for_screenshot, F.photo)
async def process_payment_screenshot(message: Message, state: FSMContext):
    try:
        await bot.send_photo(
            settings.ADMIN_GROUP_ID,
            message.photo[-1].file_id,
            caption=f"Новая оплата от пользователя {message.from_user.first_name} (ID: <code>{message.from_user.id}</code>)"
        )
        await message.answer(
            "Спасибо! Ваш платеж будет проверен администратором, после чего мы пришлем вам промокод",
            reply_markup=MainKeyboard.build_main_kb()
        )
        await state.clear()
    except Exception as e:
        logger.error(f'Ошибка при обработке скриншота: {e}')
        await message.answer('Что-то пошло не так', reply_markup=MainKeyboard.build_main_kb())