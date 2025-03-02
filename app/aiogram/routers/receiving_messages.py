import asyncio
from datetime import datetime
from loguru import logger
from aiogram import Router,F
from aiogram.types import Message,ContentType
from aiogram.filters import Command,StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from app.aiogram.common.states import TelethonBatchState
from app.db.dao import UserDAO
from app.db.database import connection
from app.db.models import User
from app.db.shemas import UserFilterModel,TelegramIDModel
from app.config import bot
receiving_message_router = Router()

@receiving_message_router.message(Command('start_batch'))
async def cmd_start_batch(message: Message, state: FSMContext):
    await state.set_state(TelethonBatchState.waiting_for_media)
    await state.update_data(media_files=[])

@receiving_message_router.message(
    StateFilter(TelethonBatchState.waiting_for_media),
    F.content_type.in_({ContentType.PHOTO, ContentType.VIDEO, ContentType.VIDEO_NOTE})
)
async def handle_telethon_media(message: Message, state: FSMContext):
    data = await state.get_data()
    media_files = data.get("media_files", [])

    if message.photo:
        media_files.append({"file_id": message.photo[-1].file_id, "media_type": 'photo'})
    elif message.video:
        media_files.append({"file_id": message.video.file_id, "media_type": 'video'})
    elif message.video_note:
        media_files.append({"file_id": message.video_note.file_id, "media_type": 'video_note'})

    await state.update_data(media_files=media_files)


send_task = None
accumulated_media_files = []
accumulated_lock = asyncio.Lock()
send_task_lock = asyncio.Lock()
@receiving_message_router.message(Command('end_batch'), TelethonBatchState.waiting_for_media)
async def end_batch(message: Message, state: FSMContext):
    global send_task

    data = await state.get_data()
    media_files = data.get("media_files", [])

    if not media_files:
        await message.reply("Вы не отправили ни одного файла.")
        await state.clear()
        return

    await message.reply("Файлы получены. Начинаю подготовку к рассылке пользователям.")

    async with accumulated_lock:
        accumulated_media_files.extend(media_files)
        logger.info(f"Аккумулировано {len(accumulated_media_files)} файлов для рассылки.")

    async with send_task_lock:
        if send_task and not send_task.done():
            send_task.cancel()
            try:
                await send_task
            except asyncio.CancelledError:
                logger.info("Предыдущая задача рассылки отменена.")

        # Создаём новую задачу с задержкой (например, 2 минуты)
        send_task = asyncio.create_task(schedule_distribute())

    await state.clear()

async def schedule_distribute(delay=40):

    try:
        logger.info(f"Задержка перед запуском рассылки: {delay} секунд.")
        await asyncio.sleep(delay)

        # Получаем все накопленные media_files
        async with accumulated_lock:
            if not accumulated_media_files:
                logger.info("Накопленные файлы для рассылки отсутствуют.")
                return
            media_files_to_send = accumulated_media_files.copy()
            accumulated_media_files.clear()
            logger.info(f"Запуск рассылки {len(media_files_to_send)} файлов.")

        await distribute_telethon_media(media_files_to_send)
    except asyncio.CancelledError:
        logger.info("Задача рассылки была отменена до запуска.")
    except Exception as e:
        logger.error(f"Ошибка в задаче schedule_distribute: {e}")


distribute_lock = asyncio.Lock()
@connection()
async def distribute_telethon_media(media_files,session,**kwargs):
    class RateLimitError(Exception):
        def __init__(self, retry_after):
            self.retry_after = retry_after
            super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")

    async def send_media_to_user(media_files:list[dict],user:User):
        try:
            for media in media_files:
                await asyncio.sleep(1)
                file_id = media.get('file_id')
                match media.get('media_type'):
                    case 'photo':
                        await bot.send_photo(user.telegram_id,file_id)
                    case 'video':
                        await bot.send_video(user.telegram_id,file_id)
                    case 'video_note':  
                        await bot.send_video_note(user.telegram_id,file_id)
        except TelegramForbiddenError:
            logger.info(f'юзер {user.telegram_id} заблокировал бота')
            user.is_blocked = True
            await UserDAO.update(session,filters=TelegramIDModel(user.telegram_id),values=TelegramIDModel.model_validate(user))
        except RateLimitError as e:
            logger.warning(f"RateLimitError при отправке видео заметки пользователю {user.id}: подождите {e.seconds} секунд.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f'при отправке медиа юзеру {user.telegram_id} произошла ошибка: {e}')

    async with distribute_lock:
        users:list[User] = await UserDAO.find_all(session=session,filters=UserFilterModel(is_blocked=False,subscription_end_gt=datetime.now()))
        logger.info(users)
        task = []
        if users:
            for user in users:
                task.append(send_media_to_user(media_files,user))
        batch_size = 10
        while task:
            current_batch = task[:batch_size]
            task = task[batch_size:]
            await asyncio.gather(*current_batch)