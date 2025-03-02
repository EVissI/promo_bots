from aiogram.fsm.state import StatesGroup, State

class ActivatePromoState(StatesGroup):
    promo = State()

class TelethonBatchState(StatesGroup):
    waiting_for_media = State()

class PaymentStates(StatesGroup):
    waiting_for_payment = State()
    waiting_for_screenshot = State()