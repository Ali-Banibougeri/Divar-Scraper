import json
import re
from pathlib import Path
from typing import Any


PERSIAN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹",
    "0123456789",
)

ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩",
    "0123456789",
)


def normalize_digits(value: str) -> str:
    return value.translate(PERSIAN_DIGITS).translate(ARABIC_DIGITS)


def parse_price(value: str | None) -> int | None:
    if not value:
        return None

    normalized = normalize_digits(value)
    digits = re.sub(r"[^\d]", "", normalized)

    if not digits:
        return None

    return int(digits)


def extract_city_code(extra_data: dict[str, Any]) -> str | None:
    jli = extra_data.get("jli", {})
    cities = jli.get("cities") if isinstance(jli, dict) else None

    if not cities:
        return None

    if isinstance(cities, list):
        if not cities:
            return None
        return str(cities[0])

    return str(cities)


def extract_category(extra_data: dict[str, Any]) -> str | None:
    jli = extra_data.get("jli", {})
    if not isinstance(jli, dict):
        return None

    category = jli.get("category", {})
    if not isinstance(category, dict):
        return None

    value = category.get("value")
    return str(value) if value is not None else None


def parse_post_row(widget: dict[str, Any]) -> dict[str, Any] | None:
    if widget.get("widget_type") != "POST_ROW":
        return None

    data = widget.get("data", {})
    if not isinstance(data, dict):
        return None

    action = data.get("action", {})
    if not isinstance(action, dict):
        action = {}

    action_payload = action.get("payload", {})
    if not isinstance(action_payload, dict):
        action_payload = {}

    token = data.get("token") or action_payload.get("token")
    if not token:
        return None

    web_info = action_payload.get("web_info", {})
    if not isinstance(web_info, dict):
        web_info = {}

    action_log = widget.get("action_log", {})
    if not isinstance(action_log, dict):
        action_log = {}

    server_side_info = action_log.get("server_side_info", {})
    if not isinstance(server_side_info, dict):
        server_side_info = {}

    info = server_side_info.get("info", {})
    if not isinstance(info, dict):
        info = {}

    extra_data = info.get("extra_data", {})
    if not isinstance(extra_data, dict):
        extra_data = {}

    price_text = data.get("middle_description_text")
    image_url = data.get("image_url")
    images = [image_url] if image_url else []

    return {
        "token": str(token),
        "title": data.get("title"),
        "price": parse_price(price_text),
        "price_text": price_text,
        "city": web_info.get("city_persian"),
        "city_code": extract_city_code(extra_data),
        "category": extract_category(extra_data),
        "last_post_sort_date": extra_data.get("last_post_sort_date"),
        "images": images,
        "image_count": data.get("image_count"),
    }


def _get_list_widgets(document: dict[str, Any]) -> list[Any]:
    direct_widgets = document.get("list_widgets")
    if isinstance(direct_widgets, list):
        return direct_widgets

    response = document.get("response", {})
    if not isinstance(response, dict):
        return []

    data = response.get("data", {})
    if not isinstance(data, dict):
        return []

    widgets = data.get("list_widgets", [])
    return widgets if isinstance(widgets, list) else []


def parse_search_response(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a Divar search response document directly in memory."""
    if not isinstance(document, dict):
        return []

    unique_ads: dict[str, dict[str, Any]] = {}

    for widget in _get_list_widgets(document):
        if not isinstance(widget, dict):
            continue

        ad = parse_post_row(widget)
        if ad is None:
            continue

        token = ad.get("token")
        if token and token not in unique_ads:
            unique_ads[token] = ad

    return list(unique_ads.values())


def parse_json_file(file_path: Path) -> list[dict[str, Any]]:
    try:
        with file_path.open("r", encoding="utf-8") as file:
            document = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []

    return parse_search_response(document)
