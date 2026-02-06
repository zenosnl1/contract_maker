# ======================================================
# Localization helpers for checkout act & documents
# ======================================================


YES_NO = {
    "ru": {
        True: "Да",
        False: "Нет",
    },
    "lv": {
        True: "Jā",
        False: "Nē",
    },
}


EARLY_INITIATOR = {
    "ru": {
        "tenant": "Арендатор",
        "landlord": "Арендодатель",
    },
    "lv": {
        "tenant": "Īrnieks",
        "landlord": "Iznomātājs",
    },
}


PAYMENT_METHOD = {
    "ru": {
        "cash": "Наличные",
        "bank_transfer": "Банковский перевод",
        "company": "С фирмы",
    },
    "lv": {
        "cash": "Skaidrā naudā",
        "bank_transfer": "Bankas pārskaitījums",
        "company": "No uzņēmuma",
    },
}


DEFAULT_LANG = "lv"


# --------------------------------------------------


def get_lang(contract: dict) -> str:
    """
    Определяем язык акта.
    Сейчас:
      - берём contract['act_language'] если появится
      - иначе LV
    """

    lang = contract.get("act_language")

    if lang in ("ru", "lv"):
        return lang

    return DEFAULT_LANG


# --------------------------------------------------


def yes_no(val: bool, lang: str) -> str:
    return YES_NO.get(lang, YES_NO[DEFAULT_LANG]).get(val, "-")


def early_initiator(val: str | None, lang: str) -> str:
    return EARLY_INITIATOR.get(lang, {}).get(val, "-")


def payment_method(val: str | None, lang: str) -> str:
    return PAYMENT_METHOD.get(lang, {}).get(val, "-")


# --------------------------------------------------


def safe(val) -> str:
    if val in (None, "", "-----"):
        return "-"
    return str(val)
