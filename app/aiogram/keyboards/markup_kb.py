from typing import Dict
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger

from app.db.models import User


del_kbd = ReplyKeyboardRemove()


def back_button():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Назад")
    return kb.as_markup(resize_keyboard=True)


class MainKeyboard:
    __user_kb_texts_dict_ru = {
        "activate_promo": "Активировать подписку",
        "check_sub": "Проверить статус подписки",
        "oplata": "Купить промокод",
        "change_lang": "Сменить язык",
    }
    __user_kb_texts_dict_en = {
        "activate_promo": "Activate subscription",
        "check_sub": "Check subscription status",
        "oplata": "Buy promo code",
        "change_lang": "Change language",
    }

    __admin_kb_text_dict_ru = {
        "change_password_for_flask_admin": "Изменить пароль админки"
    }
    __admin_kb_text_dict_en = {
        "change_password_for_flask_admin": "Change password for admin app"
    }

    @staticmethod
    def get_user_kb_texts(lang: str = "ru") -> Dict[str, str]:
        """
        'activate_promo'\n
        'check_sub'\n
        'oplata'\n
        'change_lang'
        """
        if lang == "ru":
            return MainKeyboard.__user_kb_texts_dict_ru
        elif lang == "en":
            return MainKeyboard.__user_kb_texts_dict_en
        else:
            return MainKeyboard.__user_kb_texts_dict_en

    @staticmethod
    def get_admin_kb_texts(lang: str = "ru") -> Dict[str, str]:
        """
        change_password_for_flask_admin
        """
        if lang == "ru":
            return MainKeyboard.__admin_kb_text_dict_ru
        elif lang == "en":
            return MainKeyboard.__admin_kb_text_dict_en
        else:
            return MainKeyboard.__admin_kb_text_dict_en

    @staticmethod
    def build_main_kb(user_role: User.Role, lang: str = "ru") -> ReplyKeyboardMarkup:
        kb = ReplyKeyboardBuilder()

        for val in MainKeyboard.get_user_kb_texts(lang).values():
            kb.button(text=val)

        if user_role == User.Role.admin:
            for val in MainKeyboard.get_admin_kb_texts(lang).values():
                kb.button(text=val)
        kb.adjust(
            len(MainKeyboard.get_user_kb_texts()),
            len(MainKeyboard.get_admin_kb_texts()),
        )

        return kb.as_markup(resize_keyboard=True)
