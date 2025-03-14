import asyncio
import os

from app.config import setup_logger

logger = setup_logger("user_bot")
from loguru import logger

from datetime import datetime, timedelta
from collections import defaultdict, deque

from telethon import TelegramClient, events
from telethon.tl.types import (
    Chat,
    Channel,
    MessageMediaPhoto,
    MessageMediaDocument,
    DocumentAttributeVideo,
    PeerChannel
)
from telethon.errors import FloodWaitError

from app.db.database import async_session_maker
from app.db.models import ConnectedEntity
from app.db.dao import ConnectedEntityDAO, ForwardedMessageDAO,ForwardedMessageErrorDAO
from app.db.shemas import (
    ConnectedEntityModel,
    ConnectedEntityFilter,
    ForwardedMessageErrosModel,
    ForwardedMessageModel,
    ForwardedMessageFilter,
)
from app.config import settings
from app.tools.msg_fun import split_message

# лимиты
MAX_MESSAGE_PER_SECOND = 5  # максимум 30
MAX_MESSAGES_PER_MINUTE = MAX_MESSAGE_PER_SECOND * 60
MAX_MESSAGES_PER_30_MINUTES = MAX_MESSAGES_PER_MINUTE * 30
MESSAGE_INTERVAL = 60 / MAX_MESSAGES_PER_MINUTE


client = TelegramClient(
    "my_account3",
    int(settings.USER_BOT_API_ID.get_secret_value()),
    settings.USER_BOT_API_HASH.get_secret_value(),
)

send_lock = asyncio.Lock()
message_queue = asyncio.Queue()
sent_messages_timestamps = deque()


async def is_authorized_user(event):
    if event.sender_id not in settings.ROOT_ADMIN_IDS:
        await event.reply("У вас нет прав для выполнения этой команды.")
        return False
    return True


@client.on(events.NewMessage(pattern="/help"))
async def help_command(event):
    if not await is_authorized_user(event):
        return
    help_text = (
        "📚 **Список доступных команд:**\n\n"
        "`/list_my_groups` - Показать все группы, в которых вы состоите.\n"
        "`/addgroup <ID группы>` - Добавить группу в список подключённых для пересылки сообщений.\n"
        "`/removegroup <ID группы>` - Удалить группу из списка подключённых.\n"
        "`/list_conected_groups` - Показать список всех подключённых групп.\n"
        "`/fetchhistory` - Загрузить историю сообщений из подключённых групп и переслать их основному боту.\n"
        "`/help` - Показать этот список команд.\n\n"
    )

    await event.reply(help_text, parse_mode="markdown")
    logger.info(f"Пользователь {event.sender_id} вызвал команду /help.")


@client.on(events.NewMessage(pattern="/list_my_groups"))
async def list_my_groups(event):
    if not await is_authorized_user(event):
        return
    await event.reply("Получаю список групп и каналов, пожалуйста, подождите...")

    try:
        groups = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, (Chat, Channel)):
                groups.append({"title": entity.title, "id": entity.id})

        if not groups:
            await event.reply("Я не состою в группах или каналах")
            return

        message = "Группы и каналы:\n\n"
        for group in groups:
            message += f"{group['title']} (ID: `{group['id']}`)\n"
        message = split_message(message, with_photo=False)
        for msg in message:
            await client.send_message(event.sender_id, msg)

    except Exception as e:
        logger.error(f"Ошибка при получении списка групп и каналов: {e}")
        await event.reply("Произошла ошибка при получении списка групп и каналов.")


@client.on(events.NewMessage(pattern=r"/addgroup\s+(-?\d+)"))
async def add_group(event):
    if not await is_authorized_user(event):
        return

    args = event.message.text.split()
    if len(args) < 2:
        await event.reply(
            "Пожалуйста, укажите ID группы или канала после команды /addgroup."
        )
        return

    try:
        entity_input_id = int(args[1])
        try:
            entity = await client.get_entity(entity_input_id)
            if not isinstance(entity, (Chat, Channel)):
                await event.reply("Указанный ID не принадлежит группе или каналу.")
                return

            entity_type = (
                ConnectedEntity.EntityType.group
                if isinstance(entity, Chat)
                else ConnectedEntity.EntityType.channel
            )

            async with async_session_maker() as session:
                await ConnectedEntityDAO.add(
                    session=session,
                    values=ConnectedEntityModel(
                        entity_id=entity.id,
                        entity_type=entity_type,
                        last_message_id=None,
                    ),
                )
            await event.reply(
                f'{"Группа" if entity_type.value == "group" else "Канал"} "{entity.title}" (ID: {entity.id}) добавлена в список подключённых.'
            )
            logger.info(
                f"Добавлена {'группа' if entity_type.value == 'group' else 'канал'} {entity.title} (ID: {entity.id}) пользователем {event.sender_id}."
            )
        except ValueError:
            await event.reply("Некорректный ID группы или канала.")
        except Exception as e:
            await event.reply(
                f"Не удалось получить информацию о группе/канале с ID {entity_input_id}. Возможно, юзер-бот не состоит в этой группе или канале."
            )
            logger.error(
                f"Ошибка при получении информации о сущности с ID {entity_input_id}: {e}"
            )
    except ValueError:
        await event.reply(
            "Пожалуйста, укажите корректный числовой ID группы или канала."
        )


@client.on(events.NewMessage(pattern=r"/removegroup\s+(-?\d+)"))
async def remove_group(event):
    if not await is_authorized_user(event):
        return

    args = event.message.text.split()
    if len(args) < 2:
        await event.reply("Пожалуйста, укажите ID группы или канала для удаления.")
        return

    try:
        entity_id = int(args[1])
        async with async_session_maker() as session:
            await ConnectedEntityDAO.delete(
                session=session, filters=ConnectedEntityFilter(entity_id=entity_id)
            )
            logger.info(f"Сущность {entity_id} удалена из базы данных.")
        await event.reply(f"Сущность с ID {entity_id} удалена из списка подключённых.")
        logger.info(
            f"Удалена сущность с ID {entity_id} пользователем {event.sender_id}."
        )
    except ValueError:
        await event.reply("Некорректный ID группы или канала.")
    except Exception as e:
        await event.reply(f"Не удалось удалить сущность с ID {args[1]}.")
        logger.error(f"Ошибка при удалении сущности с ID {args[1]}: {e}")


@client.on(events.NewMessage(pattern="/list_conected_groups"))
async def list_groups(event):
    if not await is_authorized_user(event):
        return

    async with async_session_maker() as session:
        entities: list[ConnectedEntity] = await ConnectedEntityDAO.find_all(
            session, ConnectedEntityFilter()
        )
    if not entities:
        await event.reply("Нет подключённых групп или каналов.")
        return

    message = "Подключённые группы и каналы:\n\n"
    for entity in entities:
        try:
            chat = await client.get_entity(entity.entity_id)
            chat_type = "Группа" if entity.entity_type.value == "group" else "Канал"
            message += f"{chat_type}: {chat.title} (ID: {chat.id})\n"
        except Exception:
            chat_type = "Группа" if entity.entity_type.value == "group" else "Канал"
            message += f"{chat_type}: Неизвестная сущность (ID: {entity.entity_id})\n"

    message = split_message(message, with_photo=False)
    for msg in message:
        await client.send_message(event.sender_id, msg)




@client.on(events.NewMessage(pattern="/fetchhistory"))
async def fetch_history(event):
    if not await is_authorized_user(event):
        return

    async with async_session_maker() as session:
        entities: list[ConnectedEntity] = await ConnectedEntityDAO.find_all(
            session, ConnectedEntityFilter()
        )
    if not entities:
        await event.reply("Нет подключённых групп или каналов для загрузки истории.")
        logger.info(
            f"Пользователь {event.sender_id} попытался загрузить историю, но подключённых групп и каналов нет."
        )
        return

    total_messages = []
    total_count = 0
    try:
        for entity in entities:
            entity_id = entity.entity_id
            entity_type = entity.entity_type.value
            count = 0
            messages_to_forward = []

            logger.info(f"Начинаю обработку сущности {entity_id} ({entity_type})")

            # Получаем ID последнего обработанного сообщения для этой сущности
            async with async_session_maker() as session:
                last_message_id = await ForwardedMessageDAO.get_max_message_id(
                    session=session, entity_id=entity_id
                )
                logger.debug(
                    f"Последний обработанный message_id для сущности {entity_id}: {last_message_id}"
                )

            # Перебираем сообщения с конца (от новых к старым)
            async for message in client.iter_messages(entity_id, reverse=False):
                # Если есть последний обработанный ID и текущий ID меньше или равен ему, прекращаем перебор
                if last_message_id is not None and message.id <= last_message_id:
                    logger.info(
                        f"Достигнут последний обработанный message_id ({last_message_id}) для сущности {entity_id}. Прекращаю перебор."
                    )
                    break
                if message.media:
                    # Проверяем тип медиа
                    if isinstance(message.media, MessageMediaPhoto):
                        pass  # Фотография подходит
                    elif isinstance(message.media, MessageMediaDocument):
                        mime_type = message.media.document.mime_type or ""
                        if mime_type.startswith("video/"):
                            pass  # Видео или изображение подходит
                        else:
                            # Проверка на видеокружку
                            is_round_video = False
                            for attr in message.media.document.attributes:
                                if isinstance(attr, DocumentAttributeVideo) and getattr(
                                    attr, "round_message", False
                                ):
                                    is_round_video = True
                                    break
                            if is_round_video:
                                pass  # Видеокружка подходит
                            else:
                                continue  # Не подходит
                    else:
                        continue  # Не подходит
                else:
                    continue  # Нет медиа
                async with async_session_maker() as session:
                    forward_message = await ForwardedMessageDAO.find_one_or_none(
                        session=session,
                        filters=ForwardedMessageFilter(
                            entity_id=entity_id, message_id=message.id
                        ),
                    )
                if forward_message:
                    continue

                messages_to_forward.append((message, entity_id))
                count += 1

            total_count += count
            total_messages.extend(messages_to_forward)
            await event.reply(
                f'Загрузка истории для {"группы" if entity_type == "group" else "канала"} {entity_id} завершена. Собрано {count} сообщений.'
            )
            logger.info(
                f"Загрузка истории для {'группы' if entity_type == 'group' else 'канала'} {entity_id} завершена. Собрано {count} сообщений."
            )
    except Exception as e:
        logger.error(f"Ошибка при загрузке истории сообщений: {e}")
        await event.reply("Произошла ошибка при загрузке истории сообщений.")

    if total_messages:
        try:
            async with async_session_maker() as session:
                for msg, entity_id in total_messages:
                    await ForwardedMessageDAO.add(
                        session=session,
                        values=ForwardedMessageModel(
                            message_id=msg.id,
                            entity_id=entity_id,
                            sent=False,
                        ),
                    )
        except Exception as e:
            logger.error(f"Ошибка при пересылке сообщений основному боту: {e}")
            await event.reply(
                "Произошла ошибка при пересылке сообщений основному боту."
            )

    await event.reply(
        f"Загрузка истории для всех групп и каналов завершена. Всего собрано {total_count} сообщений."
    )
    logger.info(
        f"Загрузка истории для всех групп и каналов завершена. Всего собрано {total_count} сообщений."
    )

async def send_forwardes_messages():
    BATCH_SIZE = 1 
    BATCH_INTERVAL = 5  
    MESSAGE_INTERVAL = 10 
    while True:
        async with async_session_maker() as session:
            messages = await ForwardedMessageDAO.get_not_sendings_messages(session,limit=BATCH_SIZE)
        if not messages:
            logger.info("Нет сообщений для пересылки")
            await asyncio.sleep(60)
            continue
        logger.info(f'Начинаю пересылку сообщений, полученно сообщений: {len(messages)}')
        await client.send_message(settings.BOT_TAG, "/start_batch")
        for message in messages:
            try:
                await client.forward_messages(settings.BOT_TAG, message.message_id, PeerChannel(message.entity_id))
                async with async_session_maker() as session:
                    message.sent = True
                    await ForwardedMessageDAO.update(
                        session=session,
                        filters=ForwardedMessageFilter(
                            entity_id=message.entity_id, message_id=message.message_id
                        ),
                        values=ForwardedMessageModel.model_validate(message.to_dict()),
                    )
                await asyncio.sleep(MESSAGE_INTERVAL)
            except Exception as e:
                logger.error(f"Ошибка при пересылке сообщения: {str(e)}")
                async with async_session_maker() as session:
                    await ForwardedMessageErrorDAO.add(
                        session=session,
                        values=ForwardedMessageErrosModel(
                            message_id=message.id,
                            error_text=str(e),
                        ),
                    )
                continue
        await client.send_message(settings.BOT_TAG, "/end_batch")
        await asyncio.sleep(BATCH_INTERVAL)

async def main():
    await client.run_until_disconnected()

with client:
    try:
        logger.info("Юзер бот включен")
        loop = asyncio.get_event_loop()
        loop.create_task(send_forwardes_messages())
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        client.disconnect()
        logger.info("Юзер бот отключен")
