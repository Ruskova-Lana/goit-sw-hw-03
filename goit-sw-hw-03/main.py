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

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def ensure_storage():
    STORAGE_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("{}", encoding="utf-8")


def load_messages() -> dict:
    ensure_storage()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_message(username: str, message: str) -> None:
    data = load_messages()
    data[str(datetime.now())] = {
        "username": username,
        "message": message,
    }

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def parse_form_data(body: bytes) -> dict:
    """
    Перетворює байт-рядок виду:
    b'username=krabaton&message=Hello+world'
    у словник:
    {'username': 'krabaton', 'message': 'Hello world'}
    """
    decoded = body.decode("utf-8")
    pairs = decoded.split("&")
    data = {}

    for pair in pairs:
        key, value = pair.split("=", 1)
        data[key] = unquote_plus(value)

    return data


class HomeworkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.render_template("index.html")
        elif self.path == "/message":
            self.render_template("message.html")
        elif self.path == "/read":
            messages = load_messages()
            # найновіші зверху
            sorted_messages = dict(sorted(messages.items(), reverse=True))
            self.render_template("read.html", {"messages": sorted_messages})
        elif self.path.startswith("/static/"):
            self.serve_static()
        else:
            self.render_template("error.html", status=404)

    def do_POST(self):
        if self.path == "/message":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = parse_form_data(body)

            username = data.get("username", "").strip()
            message = data.get("message", "").strip()

            if username or message:
                save_message(username, message)

            self.send_response(302)
            self.send_header("Location", "/read")
            self.end_headers()
        else:
            self.render_template("error.html", status=404)

    def render_template(self, template_name: str, context: dict | None = None, status: int = 200):
        context = context or {}
        template = env.get_template(template_name)
        content = template.render(**context).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_static(self):
        file_path = BASE_DIR / self.path.lstrip("/")

        if not file_path.exists() or not file_path.is_file():
            self.render_template("error.html", status=404)
            return

        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        with open(file_path, "rb") as file:
            content = file.read()

        self.send_response(200)
        self.send_header("Content-type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def run():
    ensure_storage()
    server = HTTPServer((HOST, PORT), HomeworkHandler)
    print(f"Server started at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("Server stopped.")


if __name__ == "__main__":
    run()