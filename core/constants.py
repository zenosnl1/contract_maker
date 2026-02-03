from enum import IntEnum, auto

CONTRACT_TEMPLATE = "templates/template_contract.docx"
ACT_TEMPLATE = "templates/template_act.docx"
CHECKOUT_ACT_TEMPLATE = "templates/template_checkout_act.docx"

ADMIN_USERNAMES = {
    "@zenosnl",
}

ADMIN_PHONES = {
    
}

VIEWER_USERNAMES = {
    
}

VIEWER_PHONES = {
    
}


class FlowState(IntEnum):
    MENU = 0
    FILLING = 1
    CONFIRM_SAVE = 2

    EDIT_ENTER_CODE = 10
    EDIT_ACTION = 11

    CLOSE_IS_EARLY = 20
    CLOSE_ENTER_DATE = 22

    VIOLATION_SELECT_FLAT = 40
    VIOLATION_SELECT_REASON = 41
    VIOLATION_ENTER_AMOUNT = 42
    VIOLATION_CONFIRM = 43
    VIOLATION_DELETE_SELECT_FLAT = 44
    VIOLATION_DELETE_SELECT_ITEM = 45

    CLOSE_CONFIRM_VIOLATIONS = 60

    EDIT_SELECT_ACTIVE = 70

    CLOSE_SELECT_INITIATOR = 80
    CLOSE_ENTER_EARLY_REASON = 81
    CLOSE_LANDLORD_REFUND_MODE = 82
    CLOSE_ENTER_MANUAL_REFUND = 83
    CLOSE_PREVIEW_ACT = 84

    PAYMENT_METHOD = auto()
    PAYMENT_INVOICE = auto()
    PAYMENT_INVOICE_NUMBER = auto()

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
    "MAX_PEOPLE_DAY",
    "MAX_PEOPLE_NIGHT",
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
    "MAX_PEOPLE_DAY": "Сколько человек может находиться в квартире днём?",
    "MAX_PEOPLE_NIGHT": "Сколько человек может ночевать?",
    "PRICE_PER_DAY": "Цена за ночь:",
    "DEPOSIT": "Депозит:",
}

STAT_COLUMNS = [
    "contract_code",
    "flat_number",
    "client_name",
    "client_number",

    "start_date",
    "end_date",
    "actual_checkout_date",

    "nights",
    "price_per_day",
    "total_price",
    "deposit",

    "payment_method",

    "is_closed",
]

STAT_HEADERS = {
    "contract_code": "Номер договора",
    "flat_number": "Квартира",

    "client_name": "Клиент",
    "client_number": "Телефон",

    "start_date": "Дата заезда",
    "end_date": "Дата выезда (план)",
    "actual_checkout_date": "Фактический выезд",

    "nights": "Ночей",
    "price_per_day": "Цена / ночь",
    "total_price": "Итого",
    "deposit": "Депозит",

    "payment_method": "Способ оплаты",

    "is_closed": "Статус",
}

