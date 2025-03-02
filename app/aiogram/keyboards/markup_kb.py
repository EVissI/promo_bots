from typing import Dict
from aiogram.types import ReplyKeyboardMarkup,ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger


del_kbd = ReplyKeyboardRemove()

def back_button():
    kb = ReplyKeyboardBuilder()
    kb.button(text='Назад')
    return kb.as_markup(resize_keyboard=True)

class MainKeyboard:
    __user_kb_texts_dict = {
        'activate_promo': 'Активировать подписку',
        'check_sub':'Проверить статус подписки',
        'oplata':'Купить промокод',
    }


    @staticmethod
    def get_user_kb_texts() -> Dict[str, str]:
        """
        'activate_promo'\n
        'check_sub'\n
        'oplata'
        """
        return MainKeyboard.__user_kb_texts_dict

    @staticmethod
    def build_main_kb() -> ReplyKeyboardMarkup:
        kb = ReplyKeyboardBuilder()

        for val in MainKeyboard.get_user_kb_texts().values():
            kb.button(text=val)
        kb.adjust(len(MainKeyboard.get_user_kb_texts()))

        return kb.as_markup(resize_keyboard=True)
    
    

