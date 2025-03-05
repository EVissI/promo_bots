import asyncio
from datetime import datetime
import random
from loguru import logger
from aiogram import Router, F
from aiogram.types import Message, ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from app.aiogram.common.states import TelethonBatchState
from app.db.dao import SavedMediaFileDAO, UserDAO
from app.db.database import async_session_maker
from app.db.models import User,SavedMediaFile
from app.db.shemas import UserFilterModel, TelegramIDModel, SavedMediaFileModel,SavedMediaFileFilter
from app.config import bot

receiving_message_router = Router()


@receiving_message_router.message(Command("start_batch"))
async def cmd_start_batch(message: Message, state: FSMContext):
    await state.set_state(TelethonBatchState.waiting_for_media)
    await state.update_data(media_files=[])


@receiving_message_router.message(
    StateFilter(TelethonBatchState.waiting_for_media),
    F.content_type.in_({ContentType.PHOTO, ContentType.VIDEO, ContentType.VIDEO_NOTE}),
)
async def handle_telethon_media(message: Message, state: FSMContext):
    data = await state.get_data()
    media_files = data.get("media_files", [])

    if message.photo:
        media_files.append(
            {"file_id": message.photo[-1].file_id, "media_type": SavedMediaFile.MediaTypes.photo}
        )
    elif message.video:
        media_files.append({"file_id": message.video.file_id, "media_type": SavedMediaFile.MediaTypes.video})
    elif message.video_note:
        media_files.append(
            {"file_id": message.video_note.file_id, "media_type": SavedMediaFile.MediaTypes.video_note}
        )

    await state.update_data(media_files=media_files)



@receiving_message_router.message(
    Command("end_batch"), TelethonBatchState.waiting_for_media
)
async def end_batch(message: Message, state: FSMContext):

    data = await state.get_data()
    media_files = data.get("media_files", [])

    if not media_files:
        await message.reply("Вы не отправили ни одного файла.")
        await state.clear()
        return

    await message.reply(f"Файлы получены. Всего {len(media_files)} файлов. Начинаю подготовку к рассылке пользователям.")
    logger.info(f"Файлы получены. Всего {len(media_files)} файлов.")
    async with async_session_maker() as session:
        for media in media_files:
            try:
                await SavedMediaFileDAO.add(session=session,values=SavedMediaFileModel(file_id=media.get('file_id'),file_media_type=media.get('media_type')))
            except Exception as e:
                logger.error(f'При добавлении файла в бд произошла ошибка: {e}')
                continue
        all_data = await SavedMediaFileDAO.find_all(session=session,filters=SavedMediaFileFilter())
        logger.info(f'{len(all_data)}-всего записей сейчас')
    await state.clear()





async def sending_media():
    
    async def send_media_to_user(media_files: list[SavedMediaFile], user: User):
        class RateLimitError(Exception):
            def __init__(self, retry_after):
                self.retry_after = retry_after
                super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")
        try:
            for media in media_files:
                await asyncio.sleep(random.randint(40,65))  
                file_id = media.file_id
                match media.file_media_type:
                    case SavedMediaFile.MediaTypes.photo:
                        await bot.send_photo(user.telegram_id, file_id)
                    case SavedMediaFile.MediaTypes.video:
                        await bot.send_video(user.telegram_id, file_id)
                    case SavedMediaFile.MediaTypes.video_note:
                        await bot.send_video_note(user.telegram_id, file_id)
        except TelegramForbiddenError:
            logger.info(f"юзер {user.telegram_id} заблокировал бота")
            user.is_blocked = True
            async with async_session_maker() as session:
                await UserDAO.update(
                    session,
                    filters=TelegramIDModel(telegram_id=user.telegram_id),
                    values=UserFilterModel.model_validate(user),
                )
        except RateLimitError as e:
            logger.warning(
                f"RateLimitError при отправке видео заметки пользователю {user.id}: подождите {e.seconds} секунд."
            )
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(
                f"при отправке медиа юзеру {user.telegram_id} произошла ошибка: {e}"
            )


    while True:
        try:
            async with async_session_maker() as session:
                media_files = await SavedMediaFileDAO.find_all(session=session,filters=SavedMediaFileFilter(), limit=20)
            if not media_files:
                logger.info(f'Нет сохранененных медиа файлов\n Время проверки: {datetime.now().time()}')
                await asyncio.sleep(60)
                continue
            logger.info(f"рассылка началась в :{datetime.now().time()}")
            timestamp_when_start_mailing = datetime.now()
            async with async_session_maker() as session:
                users: list[User] = await UserDAO.find_all(
                    session=session,
                    filters=UserFilterModel(
                        is_blocked=False, subscription_end_gt=datetime.now()
                    ),
                )
            task = []
            if users:
                for user in users:
                    task.append(send_media_to_user(media_files, user))
            await asyncio.gather(*task)
            async with async_session_maker() as session:
                for media in media_files:
                    await SavedMediaFileDAO.delete(session=session,filters=SavedMediaFileFilter(file_id=media.file_id))
            logger.info(
                f"f'рассылка закончилась в :{datetime.now().time()}\nЗатраченное время - {(datetime.now() - timestamp_when_start_mailing).seconds} секунд"
            )
        except Exception as e:
            logger.info(f'При рассылке медиа произошла ошибка: {str(e)}')
