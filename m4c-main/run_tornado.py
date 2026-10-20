import os
from pathlib import Path

import django
import tornado.ioloop
import tornado.web
from django.conf import settings
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer

BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "m4c.settings")

django.setup()
call_command("migrate", interactive=False, verbosity=0)
static_path = BASE_DIR / "static"
django_app = get_wsgi_application()
tornado_app = tornado.web.Application([
    (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": str(static_path)}),
    (r".*", tornado.web.FallbackHandler, {"fallback": WSGIContainer(django_app)}),
])

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    HTTPServer(tornado_app).listen(port, address=host)
    print(f"M4C running with Tornado at http://{host}:{port}")
    tornado.ioloop.IOLoop.current().start()
