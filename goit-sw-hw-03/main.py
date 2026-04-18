import json
import mimetypes
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote_plus

from jinja2 import Environment, FileSystemLoader


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
STORAGE_DIR = BASE_DIR / "storage"
DATA_FILE = STORAGE_DIR / "data.json"

HOST = "0.0.0.0"
PORT = 3000

jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def init_storage() -> None:
    STORAGE_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_data() -> dict:
    init_storage()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_post_data(data: bytes) -> dict:
    """
    Перетворює байтовий рядок форми у словник.
    Приклад:
    b'username=Ruslana&message=Hello+world'
    ->
    {'username': 'Ruslana', 'message': 'Hello world'}
    """
    decoded_data = data.decode("utf-8")
    pairs = decoded_data.split("&")
    result = {}

    for pair in pairs:
        key, value = pair.split("=", 1)
        result[key] = unquote_plus(value)

    return result


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.render_template("index.html")

        elif self.path == "/message":
            self.render_template("message.html")

        elif self.path == "/read":
            messages = load_data()
            sorted_messages = dict(sorted(messages.items(), reverse=True))
            self.render_template("read.html", {"messages": sorted_messages})

        elif self.path.startswith("/static/"):
            self.send_static()

        else:
            self.render_template("error.html", status_code=404)

    def do_POST(self):
        if self.path == "/message":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            form_data = parse_post_data(post_data)

            username = form_data.get("username", "")
            message = form_data.get("message", "")

            data = load_data()
            data[str(datetime.now())] = {
                "username": username,
                "message": message
            }
            save_data(data)

            self.send_response(302)
            self.send_header("Location", "/read")
            self.end_headers()

        else:
            self.render_template("error.html", status_code=404)

    def render_template(self, template_name: str, context: dict | None = None, status_code: int = 200):
        context = context or {}
        template = jinja_env.get_template(template_name)
        content = template.render(**context).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_static(self):
        file_path = BASE_DIR / self.path.lstrip("/")

        if not file_path.exists() or not file_path.is_file():
            self.render_template("error.html", status_code=404)
            return

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        with open(file_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def run(server_class=HTTPServer, handler_class=MyHandler):
    init_storage()
    server_address = (HOST, PORT)
    http = server_class(server_address, handler_class)
    print(f"Server started on http://localhost:{PORT}")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()
        print("Server stopped")


if __name__ == "__main__":
    run()