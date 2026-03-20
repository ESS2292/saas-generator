from fastapi import Request


THEME_COOKIE = "sg_theme"


def theme_from_request(request: Request) -> str:
    return "dark" if request.cookies.get(THEME_COOKIE) == "dark" else "light"


def theme_html_attrs(theme: str) -> tuple[str, str]:
    if theme == "dark":
        return ' data-theme="dark" class="force-dark"', ' data-theme="dark" class="force-dark"'
    return ' data-theme="light"', ' data-theme="light"'
