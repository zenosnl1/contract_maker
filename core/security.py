from telegram.ext import ConversationHandler

async def access_guard(update):

    user = update.effective_user

    if not is_user_allowed(user):
        return ConversationHandler.END

    return None


def normalize_phone(phone: str) -> str:
    return phone.replace(" ", "").replace("-", "")


def get_user_role(user):

    uname = (user.username or "").lower()

    if uname in ADMIN_USERNAMES:
        return "admin"

    if uname in VIEWER_USERNAMES:
        return "viewer"

    # телефон только если пользователь его прислал ранее
    phone = getattr(user, "phone_number", None)
    if phone:
        phone = normalize_phone(phone)

        if phone in ADMIN_PHONES:
            return "admin"

        if phone in VIEWER_PHONES:
            return "viewer"

    return None


def is_user_allowed(user) -> bool:
    return get_user_role(user) is not None
