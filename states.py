from aiogram.fsm.state import StatesGroup, State

class SetWallet(StatesGroup):
    waiting_wallet = State()

class CreateDeal(StatesGroup):
    entering = State()

class SellerOnboarding(StatesGroup):
    waiting_wallet = State()
