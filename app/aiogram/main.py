from app.config import setup_logger
from app.db.models import User

logger = setup_logger("bot")

import asyncio
from datetime import datetime
from aiogram.types import BotCommand, BotCommandScopeDefault,BotCommandScopeChat
from aiogram.exceptions import TelegramForbiddenError
from loguru import logger

from app.config import bot, admins, dp
from app.aiogram.routers.main_router import main_router
from app.db.dao import UserDAO
from app.db.database import async_session_maker
from app.db.shemas import UserFilterModel, TelegramIDModel, UserModel


async def set_commands():
\
    commands = [
        BotCommand(command="activate_promo", description="Активировать подписку"),
        BotCommand(command="check_sub", description="Проверить статус подписки"),
        BotCommand(command="oplata", description="Купить промокод"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

    async with async_session_maker() as session:
        admins:list[User] = await UserDAO.find_all(session,filters=UserFilterModel(role=User.Role.admin))

    commands.append(BotCommand(command="send_promo", description="send_promo <id юзера> <промокод>"))

    # Устанавливаем команды для каждого админа отдельно
    for admin in admins:
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=admin.telegram_id))



async def start_bot():
    await set_commands()
    for admin_id in admins:
        try:
            await bot.send_message(admin_id, f"Я запущен🥳.")
        except:
            pass
    logger.info("Бот успешно запущен.")


async def stop_bot():
    try:
        for admin_id in admins:
            await bot.send_message(admin_id, "Бот остановлен. За что?😔")
    except:
        pass
    logger.error("Бот остановлен!")


async def check_subscriptions():
    await asyncio.sleep(5)
    """Проверяет подписки пользователей, истекающие в ближайшие дни, и отправляет уведомления."""
    while True:
        try:
            async with async_session_maker() as session:
                users:list[User] = await UserDAO.find_all(
                    session,
                    filters=UserFilterModel(
                        is_blocked=False
                    ),
                )
            current_date = datetime.now()

            for user_info in users:
                user_id = user_info.telegram_id
                subscription_end = user_info.subscription_end
                if subscription_end is not None:
                    if subscription_end <= current_date:
                        user_info.promo_code = None
                        user_info.subscription_end = None
                        async with async_session_maker() as session:
                            await UserDAO.update(
                                session=session,
                                filters=TelegramIDModel(telegram_id=user_info.telegram_id),
                                values=UserModel.model_validate(user_info.to_dict()),
                            )
                        try:
                            await bot.send_message(
                                user_id,
                                "Ваша подписка истекла. Введите новый промокод для продления.",
                            )
                        except TelegramForbiddenError:
                            user_info.is_blocked = True
                            async with async_session_maker() as session:
                                await UserDAO.update(
                                    session=session,
                                    filters=TelegramIDModel(telegram_id=user_info.telegram_id),
                                    values=UserModel.model_validate(user_info.to_dict()),
                                )
                            logger.info(f"Юзер {user_info.telegram_id} заблокировал бота")
                    # Напоминания перед окончанием подписки
                    else:
                        try:
                            days_left = (subscription_end - current_date).days
                            match days_left:
                                case 3:
                                    await bot.send_message(
                                        user_id,
                                        "Ваша подписка истекает через 3 дня. Пожалуйста, продлите подписку. Your subscription expires in 3 days. Please renew your subscription.",
                                    )
                                case 2:
                                    await bot.send_message(
                                        user_id,
                                        "Ваша подписка истекает через 2 дня. Пожалуйста, продлите подписку. Your subscription expires in 2 days. Please renew your subscription.",
                                    )
                                case 1:
                                    await bot.send_message(
                                        user_id,
                                        "Ваша подписка истекает завтра. Пожалуйста, продлите подписку. Your subscription expires tomorrow. Please renew your subscription.",
                                    ) 
                                case 0:
                                    await bot.send_message(
                                        user_id,
                                        "Ваша подписка истекает сегодня. Пожалуйста, продлите подписку. Your subscription expires today. Please renew your subscription.",
                                    )
                        except TelegramForbiddenError:
                            user_info.is_blocked = True
                            async with async_session_maker() as session:
                                await UserDAO.update(
                                    session=session,
                                    filters=TelegramIDModel(telegram_id=user_info.telegram_id),
                                    values=UserModel.model_validate(user_info.to_dict()),
                                )
                            logger.info(f"Юзер {user_info.telegram_id} заблокировал бота")
        except Exception as e:
            logger.error(f"Ошибка при отправке состояния подписки: {str(e)}")
        # Запускаем проверку раз в день
        await asyncio.sleep(86400)  # 86400 секунд = 24 часа


async def main():
    # регистрация роутеров
    dp.include_router(main_router)

    # регистрация функций
    dp.startup.register(start_bot)
    dp.shutdown.register(stop_bot)
    asyncio.create_task(check_subscriptions())
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
