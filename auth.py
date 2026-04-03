import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def parse_dev_user(init_data: str | None):
    """
    Временный упрощенный режим для разработки.
    Потом заменим на реальную валидацию initData.
    """
    if not init_data:
        return {
            "id": 1,
            "first_name": "Test",
            "username": "test_user",
            "is_admin": False,
        }

    # Временный режим: если придет строка DEV_ADMIN -> админ
    if init_data == "DEV_ADMIN":
        return {
            "id": ADMIN_ID,
            "first_name": "Admin",
            "username": "admin",
            "is_admin": True,
        }

    return {
        "id": 1,
        "first_name": "Test",
        "username": "test_user",
        "is_admin": False,
    }