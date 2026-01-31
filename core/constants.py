from enum import IntEnum

CONTRACT_TEMPLATE = "template_contract.docx"
ACT_TEMPLATE = "template_act.docx"

class FlowState(IntEnum):
    MENU = 0
    FILLING = 1
    CONFIRM_SAVE = 2

    EDIT_ENTER_CODE = 10
    EDIT_ACTION = 11

    CLOSE_IS_EARLY = 20
    CLOSE_DATE_CHOICE = 21
    CLOSE_MANUAL_DATE = 22

    CLOSE_DEPOSIT = 23
    CLOSE_DEPOSIT_REASON = 24

FIELDS = [
    "FLAT_NUMBER",
    "CLIENT_NAME",
    "CLIENT_ID",
"CLIENT_ADDRESS",
"CLIENT_MAIL",
"CLIENT_NUMBER",
    "START_DATE",
    "END_DATE",
"CHECKOUT_TIME",
"PRICE_PER_DAY",
    "DEPOSIT",
]

QUESTIONS = {
    "FLAT_NUMBER": "Номер помещения:",
    "CLIENT_NAME": "Имя клиента:",
    "CLIENT_ID": "Документ / персональный код:",
"CLIENT_ADDRESS": "Адрес клиента:",
"CLIENT_MAIL": "EMAIL клиента",
"CLIENT_NUMBER": "Номер телефона клиента",
    "START_DATE": "Дата заезда:",
    "END_DATE": "Дата выезда:",
"CHECKOUT_TIME": "Время выезда:",
"PRICE_PER_DAY": "Цена за ночь:",
    "DEPOSIT": "Депозит:",
}
