from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from app.aiogram.common.messages import get_text,TEXTS_TRANSLITE

class ChangeLanguage(CallbackData, prefix="change_lang"):
    lang:str

def oplata_kb(user_language_code:str = 'ru') -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=get_text('i_am_already_pay',lang=user_language_code),callback_data='payment_done')
    return kb.as_markup()

def change_lang_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for lang in TEXTS_TRANSLITE.keys():
        kb.button(text=lang,callback_data=ChangeLanguage(
            lang=lang,
        ).pack())
    kb.adjust(len(TEXTS_TRANSLITE))
    return kb.as_markup()