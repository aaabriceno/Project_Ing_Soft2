from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
import cgi
import uuid
from templates.scripts.app_classes import Usuario,Cliente,Administrador,C_Content

session_store = {}

def generate_session_id():
    return str(uuid.uuid4())

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

paths_ulr = ["/login.html","/register.html", "/user_view.html", 
             "/admi_view.html","/addContent.html","/item_view.html",
             "/user_account.html", "/user_info.html", "/item_info_edit.html",
             "/item_view_admi.html", "/item_shop.html"]

def autenticar(username, password):
    temp_user = Usuario()
    auth = temp_user.iniciar_sesion(username, password)
    
    if auth == 1:
        user = Administrador(username, temp_user.id)
    elif auth == 0:
        user = Cliente(username, temp_user.id)
    else:
        print("Credenciales incorrectas")
        user = temp_user
    return user

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def _set_headers(self, content_type="application/json", extra_headers=None):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()

    def serve_file(self, path, content_type="text/html"):
        try:
            with open(path, "rb") as f:
                self.send_response(200)
                self.send_header("Content-type", content_type)
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Archivo no encontrado")

    def get_current_user(self):
        cookie = self.headers.get("Cookie")
        if cookie:
            for item in cookie.split(";"):
                if "session_id" in item:
                    session_id = item.split("=")[1].strip()
                    return session_store.get(session_id)
        return Usuario()
    
    def permises_web_current_user(self):
        self.send_response(403)
        self.end_headers()
        self.wfile.write(b"Usuario no autenticado")
        
    def do_GET(self):
        parsed_path = urlparse(self.path)

        current_usuario = self.get_current_user()

        if parsed_path.path == "/":
            self.serve_file(os.path.join(BASE_DIR, "templates", "main_view.html"))
        elif parsed_path.path in paths_ulr:
            self.serve_file(os.path.join(BASE_DIR, "templates", parsed_path.path[1:]))
        elif parsed_path.path.startswith("/static") or parsed_path.path.startswith("/styles") or parsed_path.path.startswith("/scripts"):
            file_path = os.path.join(BASE_DIR, "templates", parsed_path.path[1:])
            ext = os.path.splitext(file_path)[1]
            mime_types = {
                ".html": "text/html", ".js": "application/javascript", ".css": "text/css",
                ".jpg": "image/jpeg", ".png": "image/png", ".mp4": "video/mp4", ".mp3": "audio/mpeg"
            }
            content_type = mime_types.get(ext, "application/octet-stream")
            self.serve_file(file_path, content_type)

        elif parsed_path.path == "/main_view_content":
            self._set_headers()
            self.wfile.write(json.dumps(C_Content.getContentView()).encode("utf-8"))

        elif parsed_path.path == "/get_balance":
            if current_usuario:
                self._set_headers()
                self.wfile.write(json.dumps({"success":True, "saldo":current_usuario.getSaldo()}).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/user_data":
            if current_usuario:
                self._set_headers()
                self.wfile.write(json.dumps(current_usuario.getDataUser()).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/get_recargas":
            if current_usuario and isinstance(current_usuario, Administrador):
                self._set_headers()
                self.wfile.write(json.dumps(current_usuario.obtenerRecargas()).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/get_notificaciones":
            if current_usuario and isinstance(current_usuario, Cliente):
                self._set_headers()
                self.wfile.write(json.dumps(current_usuario.obtenerNotificaciones()).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/get_user_role":
            if current_usuario and isinstance(current_usuario, Cliente):
                self._set_headers()
                self.wfile.write(json.dumps({"role":"Cliente"}).encode("utf-8"))
            elif current_usuario and isinstance(current_usuario, Administrador):
                self._set_headers()
                self.wfile.write(json.dumps({"role":"Administrador"}).encode("utf-8"))                
            else:
                self._set_headers()
                self.wfile.write(json.dumps({"role":"User"}).encode("utf-8")) 

        elif parsed_path.path == "/get_user_downloads":
            if current_usuario and isinstance(current_usuario, Cliente):
                self._set_headers()
                self.wfile.write(json.dumps(current_usuario.obtenerDescargasCliente()).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/close_account":
            if current_usuario and isinstance(current_usuario, Cliente):
                self._set_headers()
                self.wfile.write(json.dumps({'success':current_usuario.SolicitarValidarSaldo()}).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/logout_account":
            if current_usuario:
                print(session_store)
                cookie_header = self.headers.get("Cookie")
                session_id = None

                if cookie_header:
                    cookies = dict(cookie.strip().split("=", 1) for cookie in cookie_header.split(";") if "=" in cookie)
                    session_id = cookies.get("session_id")

                if session_id and session_id in session_store:
                    del session_store[session_id]

                # Invalida la cookie enviando una expiración pasada
                expired_cookie = "session_id=deleted; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
                self.send_response(302)
                self.send_header("Set-Cookie", expired_cookie)
                self.send_header("Location", "/login.html")
                self.end_headers()
                print(session_store)
            else:
                self.permises_web_current_user()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Ruta GET no encontrada")

    def do_POST(self):
        parsed_path = urlparse(self.path)
        content_type = self.headers.get('Content-Type', '')

        data = {}
        form = None
        current_usuario = self.get_current_user()

        if not content_type.startswith('multipart/form-data'):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = parse_qs(body)

        if parsed_path.path == "/signin":
            name = data.get("name")
            password = data.get("password")
            if isinstance(name, list): name = name[0]
            if isinstance(password, list): password = password[0]

            user = autenticar(name, password)

            if isinstance(user, Cliente) or isinstance(user, Administrador):
                session_id = generate_session_id()
                session_store[session_id] = user
                extra_headers = {"Set-Cookie": f"session_id={session_id}; Path=/"}
                redirect_url = "admi_view.html" if isinstance(user, Administrador) else "user_view.html"
                response = {"success": True, "url": redirect_url}
                self._set_headers(extra_headers=extra_headers)
            else:
                response = {"success": False, "message": "Credenciales inválidas"}
                self._set_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif parsed_path.path == "/search_content":
            if current_usuario:
                resultados = current_usuario.Buscar(data.get("query"), data.get("filters"))
                self._set_headers()
                self.wfile.write(json.dumps(resultados).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/search_info":
            if current_usuario:
                print(data)
                self._set_headers()
                resultados = current_usuario.buscar_info(data)
                print(resultados)
                self.wfile.write(json.dumps(resultados).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/request_balance":
            if current_usuario:
                response = current_usuario.ingresarMontoSolicitar(data.get("tarjeta"), data.get("cantidad"), data.get("cardType"))
                self._set_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/accept_recarga":
            if current_usuario:
                current_usuario.aprobarSaldoCliente(int(data.get("id_recarga")))
                self._set_headers()
                self.wfile.write(json.dumps({"success":True}).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/accept_notificacion":
            if current_usuario:
                current_usuario.aceptarNotificacion(int(data.get("id_recarga")))
                self._set_headers()
                self.wfile.write(json.dumps({"success":True}).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/get_content_by_id":
            if current_usuario:
                content_id = int(data.get("id", 0))
                found = current_usuario.seleccionar(content_id)
                self._set_headers()
                self.wfile.write(json.dumps(found or {"error": "Contenido no encontrado"}).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/download_content":
            if current_usuario:
                content_id = int(data.get("id", 0))
                cont = C_Content()
                contenido = cont.obtenerBinarioPorID(content_id)  

                if contenido:
                    bin_data = contenido['src']
                    extension = contenido['extension']
                    filename = contenido['title'].replace(" ", "_") + "." + extension

                    mime_map = {
                        # Imágenes
                        "png": "image/png",
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "gif": "image/gif",
                        "bmp": "image/bmp",
                        "webp": "image/webp",
                        "svg": "image/svg+xml",
                        "tiff": "image/tiff",
                        "ico": "image/x-icon",

                        # Audio
                        "mp3": "audio/mpeg",
                        "wav": "audio/wav",
                        "ogg": "audio/ogg",
                        "aac": "audio/aac",
                        "flac": "audio/flac",
                        "m4a": "audio/mp4",
                        "mid": "audio/midi",
                        "oga": "audio/ogg",

                        # Video
                        "mp4": "video/mp4",
                        "webm": "video/webm",
                        "mov": "video/quicktime",
                        "avi": "video/x-msvideo",
                        "mkv": "video/x-matroska",
                        "flv": "video/x-flv",
                        "wmv": "video/x-ms-wmv",
                        "3gp": "video/3gpp",
                    }
                    mime_type = mime_map.get(extension.lower(), "application/octet-stream")

                    self.send_response(200)
                    self.send_header("Content-Type", mime_type)
                    self.send_header("Content-Disposition", f"attachment; filename={filename}")
                    self.send_header("Content-Length", str(len(bin_data)))
                    self.end_headers()

                    self.wfile.write(bin_data)
                else:
                    self.send_error(404, "Contenido no encontrado")
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/get_user_by_id":
            if current_usuario:
                id = int(data.get("id", 0))
                found = current_usuario.seleccionar_user(id)
                self._set_headers()
                self.wfile.write(json.dumps(found or {"error": "usuario no encontrado"}).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/save_content":
            if current_usuario and isinstance(current_usuario, Administrador):
                print("AEA")
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST'},
                )

                fileitem = form['file']
                if fileitem.filename:
                    filename = fileitem.filename
                    binary_data = fileitem.file.read()  # Aquí están los bytes del archivo

                    title = form.getvalue("content-title")
                    author = form.getvalue("content-author")
                    price = form.getvalue("content-price")
                    extension = filename.split('.')[-1]
                    content_type = form.getvalue("content-type")
                    category = form.getvalue("content-category")
                    description = form.getvalue("content-description")

                    new_item = {
                        "src": binary_data,  # Guarda como BLOB
                        "title": title,
                        "author": author,
                        "price": price,
                        "extension": extension,
                        "category": category,
                        "rating": 0,
                        "description": description,
                        "type": content_type
                    }

                    current_usuario.ingresarAgregarContenido(new_item)
                    response = {"success": True, "message": "Contenido guardado"}
                    #print(binary_data)
                    #print(new_item)
                else:
                    response = {"success": False, "message": "No se recibió archivo"}

                self._set_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))

        elif parsed_path.path == "/register":
            name = data.get("name")
            password = data.get("password")
            email = data.get("email")

            if isinstance(name, list): name = name[0]
            if isinstance(password, list): password = password[0]
            if isinstance(email, list): email = email[0]

            new_user = Usuario()
            print(name, password, email)
            resultado = new_user.validarRegistro(name, password, email)

            if resultado == 0:
                response = {"success": False, "message": "El usuario ya existe."}
            elif resultado == 1:
                response = {"success": True, "message": "Registro exitoso."}
            else:
                response = {"success": False, "message": "Error al registrar usuario."}

            self._set_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif parsed_path.path == "/verificate_downloaded_content":
            if current_usuario and isinstance(current_usuario, Administrador):
                self._set_headers()
                self.wfile.write(json.dumps({'success':True}).encode("utf-8"))
            elif current_usuario and isinstance(current_usuario, Cliente):
                self._set_headers()
                canDownload = current_usuario.verificarContenido(data.get("id"))
                self.wfile.write(json.dumps(canDownload).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/pagarContenido":
            if current_usuario and isinstance(current_usuario, Administrador):
                self._set_headers()
                self.wfile.write(json.dumps({'success':True, 'hasRated':True}).encode("utf-8"))
            elif current_usuario and isinstance(current_usuario, Cliente):
                self._set_headers()
                canDownload = current_usuario.pagarContenido(data.get("id"))
                self.wfile.write(json.dumps({'success':canDownload}).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/rate_content":
            if current_usuario and isinstance(current_usuario, Cliente):
                self._set_headers()
                #print((data.get("id"), data.get("score")), "ratee")
                hasRated = current_usuario.Enviar_Puntuacion(data.get("id"), data.get("score"))
                self.wfile.write(json.dumps({'success':hasRated}).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/gift_content":
            if current_usuario and isinstance(current_usuario, Cliente):
                self._set_headers()
                print(data.get("id"), data.get("destinatario"))
                canGift = current_usuario.Enviar_destinatario(data.get("id"), data.get("destinatario"))
                self.wfile.write(json.dumps(canGift).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/withdraw_balance":
            if current_usuario and isinstance(current_usuario, Cliente):
                self._set_headers()
                res = {'success':current_usuario.Retirar_Saldo(data.get("tarjeta"), data.get("cardType"))}
                self.wfile.write(json.dumps(res).encode("utf-8"))
            else:
                self.permises_web_current_user()

        elif parsed_path.path == "/get_user_downloads_info":
            if current_usuario and isinstance(current_usuario, Administrador):
                self._set_headers()
                self.wfile.write(json.dumps(current_usuario.obtenerDescargasCliente(data.get("id"))).encode("utf-8"))
            else:
                self.permises_web_current_user()           
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Ruta POST no encontrada")


def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler):
    server_address = ('', 3000)
    httpd = server_class(server_address, handler_class)
    print("Servidor corriendo en http://localhost:3000/")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
