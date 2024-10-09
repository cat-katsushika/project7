from django.conf import settings


def get_frontend_url(memo_id) -> str:
    """フロントエンドのページのURLを返す関数."""
    client_base_url = settings.CLIENT_BASE_URL
    return f"{client_base_url}/?id={memo_id}"
