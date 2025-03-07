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
)
from telethon.errors import FloodWaitError

from app.db.database import async_session_maker
from app.db.models import ConnectedEntity
from app.db.dao import ConnectedEntityDAO, ForwardedMessageDAO
from app.db.shemas import (
    ConnectedEntityModel,
    ConnectedEntityFilter,
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


client = TelegramClient("my_account3",int(settings.USER_BOT_API_ID.get_secret_value()), settings.USER_BOT_API_HASH.get_secret_value())

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


BATCH_SIZE = 25  # Максимальный размер батча для Telegram API
BATCH_INTERVAL = 10  # Задержка между батчами в секундах


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
                        if mime_type.startswith("video/") or mime_type.startswith(
                            "image/"
                        ):
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

            for i in range(0, len(total_messages), BATCH_SIZE):
                batch = total_messages[i : i + BATCH_SIZE]
                messages_batch = [msg for msg, entity_id in batch]
                logger.info(f"Отправка батча из {len(batch)} сообщений.")

                # Отправляем команду /start_batch
                await client.send_message(settings.BOT_TAG, "/start_batch")
                logger.info("Отправлена команда /start_batch основному боту.")

                # Пересылаем батч сообщений
                await client.forward_messages(settings.BOT_TAG, messages_batch)
                logger.info(f"Пересланы {len(batch)} сообщений основному боту.")

                # Отправляем команду /end_batch
                await client.send_message(settings.BOT_TAG, "/end_batch")
                logger.info("Отправлена команда /end_batch основному боту.")

                # Отмечаем сообщения как пересланные после успешной отправки
                async with async_session_maker() as session:
                    for message, entity_id in batch:

                        await ForwardedMessageDAO.add(
                            session=session,
                            values=ForwardedMessageModel(
                                message_id=message.id, entity_id=entity_id, sent=True
                            ),
                        )

                # Задержка между отправками батчей
                await asyncio.sleep(BATCH_INTERVAL)
        except FloodWaitError as e:
            logger.warning(
                f"FloodWaitError при пересылке сообщений: Подождите {e.seconds} секунд."
            )

            async with async_session_maker() as session:
                for message, entity_id in total_messages[i:]:
                    await ForwardedMessageDAO.add(
                        session=session,
                        values=ForwardedMessageModel(
                            message_id=message.id, entity_id=entity_id, sent=False
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


client.on(events.NewMessage())
async def forward_new_messages(event):
    logger.debug(
        f"Получено новое сообщение из chat_id={event.chat_id}, тип={type(event.chat_id)}"
    )
    async with async_session_maker() as session:
        entities:list[ConnectedEntity] = await ConnectedEntityDAO.find_all(session=session,filters=ConnectedEntityFilter())
        logger.debug(
            f"Подключённые сущности: {entities}, типы ID сущностей: {[type(e.entity_id) for e in entities]}"
        )

    try:
        # Получаем сущность чата
        entity = await event.get_chat()
        entity_id = entity.id
        logger.debug(f"entity.id для текущего чата: {entity_id}")
    except Exception as e:
        logger.error(f"Не удалось получить entity для chat_id={event.chat_id}: {e}")
        return

    # Найдём соответствующую запись
    connected_chat = next((e for e in entities if e["id"] == entity_id), None)
    if not connected_chat:
        logger.debug("Сообщение не из подключённой группы или канала")
        return

    logger.debug(
        f"Сообщение из подключённой {'группы' if connected_chat['type'] == 'group' else 'канала'}"
    )

    if event.message.media:
        media_type = type(event.message.media)
        logger.debug(f"Сообщение содержит медиа типа: {media_type}")
        if isinstance(event.message.media, MessageMediaPhoto):
            logger.debug("Медиа — фотография")
        elif isinstance(event.message.media, MessageMediaDocument):
            mime_type = event.message.media.document.mime_type
            logger.debug(f"MIME тип документа: {mime_type}")
            if mime_type.startswith("video/"):
                logger.debug("Медиа — видео")
            else:
                logger.debug("Проверка на видеокружку")
                is_round_video = False
                for attr in event.message.media.document.attributes:
                    if isinstance(attr, DocumentAttributeVideo) and getattr(
                        attr, "round_message", False
                    ):
                        is_round_video = True
                        break
                if is_round_video:
                    logger.debug("Медиа — видеокружка")
                else:
                    logger.debug("Неподдерживаемый тип медиа")
                    return
        else:
            logger.debug("Неподдерживаемый тип медиа")
            return

        async with async_session_maker() as session:
            if await ForwardedMessageDAO.find_one_or_none(
                session=session,
                filters=ForwardedMessageFilter(
                    message_id=event.message.id, entity_id=entity_id
                ),
            ):
                logger.debug("Сообщение уже было обработано")
                return  # Пропускаем уже обработанные сообщения

        # Добавляем сообщение в очередь для отправки
        try:
            await message_queue.put((event.message, entity_id))
            logger.debug("Сообщение добавлено в очередь для пересылки")
        except Exception as e:
            logger.error(f"Исключение при добавлении сообщения в очередь: {e}")
    else:
        logger.debug("Сообщение не содержит медиа")


async def process_message_queue():
    while True:
        batch = []
        try:
            # Ожидаем первое сообщение с таймаутом
            message_tuple = await asyncio.wait_for(message_queue.get(), timeout=5)
            batch.append(message_tuple)

            # Собираем дополнительные сообщения в течение BATCH_INTERVAL
            start_time = asyncio.get_event_loop().time()
            while len(batch) < BATCH_SIZE:
                time_left = BATCH_INTERVAL - (
                    asyncio.get_event_loop().time() - start_time
                )
                if time_left <= 0:
                    break
                try:
                    message_tuple = await asyncio.wait_for(
                        message_queue.get(), timeout=time_left
                    )
                    batch.append(message_tuple)
                except asyncio.TimeoutError:
                    break  # Нет новых сообщений в течение оставшегося времени

            if batch:
                async with send_lock:
                    try:
                        # Отправляем команду /start_batch
                        await client.send_message(settings.BOT_TAG, "/start_batch")
                        logger.info("Отправлена команда /start_batch основному боту.")

                        # Подготавливаем сообщения для отправки
                        messages = [msg for msg, entity_id in batch]

                        # Пересылаем все сообщения в пачке одним вызовом
                        await client.forward_messages(settings.BOT_TAG, messages)
                        logger.info(f"Пересланы {len(batch)} сообщений основному боту.")

                        # Отправляем команду /end_batch
                        await client.send_message(settings.BOT_TAG, "/end_batch")
                        logger.info("Отправлена команда /end_batch основному боту.")

                        async with async_session_maker() as session:
                            for msg, entity_id in batch:
                                await ForwardedMessageDAO.add(
                                    session=session,
                                    values=ForwardedMessageModel(
                                        msg.id, entity_id, sent=True
                                    ),
                                )

                        logger.debug(f"Отправлена пачка из {len(batch)} сообщений.")
                    except FloodWaitError as e:
                        logger.warning(
                            f"FloodWaitError при пересылке сообщений: Подождите {e.seconds} секунд."
                        )

                        # Устанавливаем retry_at для сообщений и не помечаем их как отправленные
                        retry_at = datetime.now() + timedelta(seconds=e.seconds)
                        async with async_session_maker() as session:
                            for msg, entity_id in batch:
                                await ForwardedMessageDAO.add(
                                    session=session,
                                    values=ForwardedMessageModel(
                                        msg.id, entity_id, sent=False
                                    ),
                                )
                        # Сообщения будут повторно отправлены функцией retry_failed_messages
                    except Exception as e:
                        logger.error(
                            f"Ошибка при пересылке сообщений основному боту: {e}"
                        )
                        # Сообщения не будут повторно отправлены
                        async with async_session_maker() as session:
                            for msg, entity_id in batch:
                                await ForwardedMessageDAO.add(
                                    session=session,
                                    values=ForwardedMessageModel(
                                        msg.id, entity_id, sent=False
                                    ),
                                )
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.error(f"Ошибка при обработке очереди сообщений: {e}")


async def retry_failed_messages():
    while True:
        # Ждём 30 минут перед каждой попыткой
        await asyncio.sleep(1800)

        logger.info("Начало попытки повторной отправки сообщений.")

        async with async_session_maker() as session:
            messages_to_retry = await ForwardedMessageDAO.find_all(
                session, filters=ForwardedMessageFilter(sent=False)
            )

        if not messages_to_retry:
            logger.info("Нет сообщений для повторной отправки.")
            continue

        messages_grouped = defaultdict(list)
        for record in messages_to_retry:
            messages_grouped[record["entity_id"]].append(record["message_id"])
        async with send_lock:
            for entity_id, message_ids in messages_grouped.items():
                try:
                    # Получаем сообщения для пересылки
                    messages = await client.get_messages(entity_id, ids=message_ids)

                    # Отправляем команду /start_batch основному боту
                    await client.send_message(settings.BOT_TAG, "/start_batch")
                    logger.info("Отправлена команда /start_batch основному боту.")

                    # Пересылаем сообщения основному боту
                    await client.forward_messages(settings.BOT_TAG, messages)
                    logger.info(
                        f"Пересланы {len(messages)} сообщений основному боту при повторной отправке."
                    )

                    # Отправляем команду /end_batch основному боту
                    await client.send_message(settings.BOT_TAG, "/end_batch")
                    logger.info("Отправлена команда /end_batch основному боту.")

                    async with async_session_maker as session:
                        for message_id in message_ids:
                            await ForwardedMessageDAO.update(
                                session=session,
                                filters=ForwardedMessageFilter(
                                    entity_id=entity_id, message_id=message_id
                                ),
                                values=ForwardedMessageFilter(sent=True),
                            )
                    logger.info(
                        f"Сообщения от сущности {entity_id} помечены как отправленные."
                    )
                except FloodWaitError as e:
                    logger.warning(
                        f"FloodWaitError при повторной отправке сообщений от сущности {entity_id}"
                    )

                    break
                except Exception as e:
                    logger.error(
                        f"Ошибка при повторной отправке сообщений от сущности {entity_id}: {e}"
                    )
                    continue


async def main():
    await client.run_until_disconnected()
    asyncio.create_task(process_message_queue())
    asyncio.create_task(retry_failed_messages())

with client:
    try:
        logger.info("Юзер бот включен")
        loop = asyncio.get_event_loop()
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        client.disconnect()
        logger.info("Юзер бот отключен")
