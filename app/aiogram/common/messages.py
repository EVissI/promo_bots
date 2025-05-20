def get_text(text_code:str, lang:str = 'ru',**kwargs) -> str:
    text = ''
    if lang == 'ru':
        text = TEXTS_TRANSLITE['ru'].get(text_code,text_code)
    elif lang == 'en':
        text = TEXTS_TRANSLITE['en'].get(text_code,text_code)
    else:
        text = TEXTS_TRANSLITE['en'].get(text_code,text_code)
    return text.format(**kwargs)

TEXTS_TRANSLITE ={
    'ru':{
        'start_msg':"Привет! Я бот для покупки промокодов. Для начала работы нажмите кнопку 'Начать'",
        'user_is_banned':"К сожалению, вы заблокированны в боте",
        'only_admins_can_use_this_functionality':"Только администраторы могут пользоваться этим функционалом",
        'i_am_already_pay':"Я уже оплатил",
        'promo_message': "Ваш промокод: <code>{promo_code}</code> \nДля активации подписки нажмите кнопку '{activate_button}'",
        'user_is_not_registered':'Для использования ботом пройдите регистрацию через команду /start',
        'have_no_sub': 'У вас нет активной подписки',
        'sub_is_end':'Ваша подписка закончилась',
        'sub_is_active':"Ваша подписка активна еще {days_left} дней\nДата окончания: {end_date}",
        'promocode_is_not_found':'Промокод не найден',
        'promocode_is_was_used':'Промокод уже был использован', 
        'promocode_used_successfully':'Промокод успешно активирован, подписка кончится: {end_date}',
        'payment_form': "Для оплаты переведите по номеру {phone_number}: {payment_amount}₽",
        'payment_check_pls' : 'Пришлите чек оплаты, пожалуйста',
        'change_language':'Выберите язык',
        'language_changed':'Язык изменен',
        'ty_yr_payment_was_successfully':'Спасибо! Ваш платеж будет проверен администратором, после чего мы пришлем вам промокод',
        'insert_new_pass':'Введите новый пароль',
        'change_pass_successful':'Пароль был успешно изменен',
        'error_no_arguments_passed': 'Ошибка: не переданы аргументы',
        'error_wrong_promo_args': 'Ошибка: неправильный формат команды. Пример:\n/send_promo <id> <promo>',
        'error_promo_args':'Ошибка: не передан промокод',
        'error_user_not_found':'Ошибка: не найден юзер',
        'error_promo_not_found':'Ошибка: не найден промокод',
        'error_somthing_went_wrong':'Что-то пошло не так',
        'oplata_temporarily':'По поводу подписки обращайтесь к администратору https://t.me/hc_et'
    },
    'en':{
        'start_msg':"Привет! Я бот для покупки промокодов. Для начала работы нажмите кнопку 'Начать'",
        'user_is_banned':"Sorry, you are blocked in the bot",
        'only_admins_can_use_this_functionality':"Only admins can use this functionality",
        'i_am_already_pay':"I am already pay",
        'promo_message': "Your promo code: <code>{promo_code}</code> \nTo activate the subscription, press the '{activate_button}' button",
        'user_is_not_registered':'To use the bot, register via the /start command',
        'have_no_sub': 'You have no active subscription',
        'sub_is_end':'Your subscription has ended',
        'sub_is_active':"Your subscription is active for another {days_left} days\nEnd date: {end_date}",
        'promocode_is_not_found':'Promocode not found',
        'promocode_is_was_used':'Promocode was used',
        'promocode_used_successfully':'Promocode successfully activated, subscription ends: {end_date}',
        'payment_form': "To pay, transfer to the number {phone_number}: {payment_amount}₽",
        'payment_check_pls' : 'Please send the payment receipt',
        'change_language':'Choose language',
        'language_changed':'Language changed',
        'ty_yr_payment_was_successfully':'Thank you! Your payment will be checked by the administrator, after which we will send you a promo code',
        'insert_new_pass':'Type new password',
        'change_pass_successful':'Password was update',
        'error_no_arguments_passed': 'Error: no arguments passed',
        'error_promo_args':'Error: no promo passed',
        'error_wrong_promo_args': 'Error: wrong command format. Example:\n/send_promo <id> <promo>',
        'error_user_not_found':'Error: user not found',
        'error_promo_not_found':'Error: promo not found',
        'error_somthing_went_wrong':'Something went wrong',
    }

}