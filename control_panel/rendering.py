from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


TEMPLATE_DIR = Path(__file__).with_name("templates")


# Keep the environment local to the control panel package so the HTML layer is
# separate from the route/controller logic in web_app.py.
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_template(name: str, **context) -> str:
    return env.get_template(name).render(**context)
