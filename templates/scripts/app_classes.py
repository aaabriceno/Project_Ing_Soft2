from datetime import datetime
import sqlite3
import base64

DB_PATH = 'templates/static/db/downez.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

class E_Usuarios:
    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def registrar_Excliente(self, idU):
        query = "UPDATE usuarios SET estado_cuenta = 'ex-cliente' WHERE id = ?"
        self.cursor.execute(query, (idU,))
        self.conn.commit()

    def verificarLogin(self, username, password):
        query = """
        SELECT 
                auth, id 
            FROM 
                usuarios 
            WHERE 
                username = ? AND pswd = ? AND (estado_cuenta = 'cliente' OR estado_cuenta = 'administrador')
        """
        self.cursor.execute(query, (username, password))
        result = self.cursor.fetchone()
        if result:
            return result[0], result[1]  # tipo (Administrador/Cliente), id_usuario
        return None, None

    def obtenerUser(self, id_usuario):
        query="SELECT username, email, saldo, estado_cuenta FROM usuarios WHERE id = ?"
        self.cursor.execute(query, (id_usuario,))
        resultado = self.cursor.fetchone()

        if resultado:
            return {
                "username": resultado[0],
                "email": resultado[1],  
                "saldo": resultado[2],
                "estado":resultado[3]
            }
        return None

    def obtenerSaldo(self, id):
        query = "SELECT saldo FROM usuarios WHERE id = ?"
        self.cursor.execute(query, (id,))
        result = self.cursor.fetchone()
        print(result)
        if result:
            return result[0]
        return None

    def actualizarSaldo(self,id, cantidad):
        query = "UPDATE usuarios SET saldo = saldo + ? WHERE id = ?"
        self.cursor.execute(query, (cantidad, id))
        self.conn.commit()

    def validarDatos(self, username):
        query = "SELECT id FROM usuarios WHERE username = ? AND (estado_cuenta = 'cliente' OR estado_cuenta = 'administrador')"
        self.cursor.execute(query, (username,))
        result = self.cursor.fetchone()
        return result is None # si es none, es porque no se encontro, por ende no existe ese usuario a registrar :D
    
    def UsuarioExiste(self, username, idU):
        query = "SELECT id FROM usuarios WHERE username = ? AND id != ? AND estado_cuenta = 'cliente'"
        self.cursor.execute(query, (username,idU))
        result = self.cursor.fetchone()
        return -1 if result is None else result[0]
        
    def registrarUsuario(self, username, password, email):
        query = "INSERT INTO usuarios (username, pswd, email) VALUES (?, ?, ?)"
        print("A")
        self.cursor.execute(query, (username, password, email))
        self.conn.commit()
    
    def buscar_info_usuarios(self, query):
        q_like = f"%{query.lower()}%"
        sql = "SELECT id, username, email, estado_cuenta FROM usuarios WHERE CAST(id AS TEXT) LIKE ? OR LOWER(username) LIKE ?"
        self.cursor.execute(sql, (q_like,q_like))
        result = self.cursor.fetchall()

        lista = []
        for row in result:
            lista.append({
                "id": row[0],
                "title": row[1],
                "author": row[2],
                "type": row[3],
            })
        return lista

class E_Transacciones:
    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def verificarContenido(self, idu, idc):
        query = "SELECT id_contenido, id_usuario FROM transacciones WHERE id_contenido = ? AND id_usuario = ?"
        self.cursor.execute(query, (idc,idu,))
        result = self.cursor.fetchone()
        #print(result)
        if(result is None): return False
        return True
    
    def registrarCompra(self, idU, idC,precio, type_trans="compra"):
        query = "INSERT INTO transacciones (id_usuario,id_contenido, precio, fecha, tipo_transaccion) VALUES (?, ?, ?, ?,?)"
        fecha = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.cursor.execute(query, (idU, idC, precio, fecha,type_trans))
        transaccion_id = self.cursor.lastrowid  # obtiene el ID insertado
        self.conn.commit()
        return transaccion_id

    def obtenerDescargasCliente(self, id_usuario):
        query = """
            SELECT c.title, c.rating, c.type, c.author, c.id
            FROM transacciones uc
            JOIN contenidos c ON uc.id_contenido = c.id
            WHERE uc.id_usuario = ?
        """
        self.cursor.execute(query, (id_usuario,))
        results = self.cursor.fetchall()
        lista = []
        for row in results:
            lista.append({
                "title": row[0],
                "rating": row[1],
                "type": row[2],
                "author": row[3],
                "id": row[4]
            })
        return lista

class E_Regalos(E_Transacciones):
    def __init__(self):
        super().__init__()

    def registrarRegalo(self, idU, idC, precio, type_trans, id_des):
        id_trans = self.registrarCompra(idU,idC,precio,type_trans)
        query = "INSERT INTO regalos (id_transaccion, id_destinatario) VALUES (?, ?)"
        self.cursor.execute(query, (id_trans,id_des))
        self.conn.commit()

    def verificarContenidoDestinatario(self, id_des, idc):
        query = """
            SELECT 
                t.id
            FROM 
                transacciones t
            JOIN 
                regalos r ON t.id = r.transaccion_id
            WHERE 
                t.id_contenido = ? AND r.destinatario_id = ?
        """
        self.cursor.execute(query, (idc, id_des))
        result = self.cursor.fetchone()
        return result is not None
    
class E_Puntuaciones:
    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def Registrar_Puntuacion(self, user_id, id_contenido, puntuacion):
        # Paso 1: Insertar nueva puntuación
        insert_query = "INSERT INTO puntuaciones (id_contenido, id_cliente, puntuacion) VALUES (?, ?, ?)"
        self.cursor.execute(insert_query, (id_contenido, user_id, puntuacion))
        self.conn.commit()

        # Paso 2: Calcular el nuevo promedio de puntuaciones
        promedio_query = "SELECT AVG(puntuacion) FROM puntuaciones WHERE id_contenido = ?"
        self.cursor.execute(promedio_query, (id_contenido,))
        promedio = self.cursor.fetchone()[0]

        # Paso 3: Actualizar el campo 'rating' en la tabla contenidos
        update_query = "UPDATE contenidos SET rating = ? WHERE id = ?"
        self.cursor.execute(update_query, (promedio, id_contenido))
        self.conn.commit()

    def Existe_Puntuacion(self, idU,idC):
        query = "SELECT * FROM puntuaciones WHERE id_cliente = ? AND id_contenido = ?"
        self.cursor.execute(query, (idU,idC,))
        result = self.cursor.fetchone()
        if(result is None): return False
        return True

class E_Notificaciones:
    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def registrarNotificacionRegalo(self, idU, idC, msg):
        query = "INSERT INTO notificaciones (id_usuario, id_contenido, messagge) VALUES (?, ?, ?)"
        self.cursor.execute(query, (idU, idC, msg))
        self.conn.commit()

    def registrarNotificacionRecarga(self, idU, msg):
        query = "INSERT INTO notificaciones (id_usuario, id_contenido, messagge) VALUES (?, ?, ?)"
        self.cursor.execute(query, (idU, -1, msg))
        self.conn.commit()

    def obtenerListaNotificaciones(self, idU):
        query = """
                SELECT 
                    n.id,
                    c.id, 
                    c.title, 
                    n.messagge
                FROM 
                    notificaciones n
                JOIN 
                    contenidos c ON c.id = n.id_contenido
                WHERE 
                    n.id_usuario = ?
            """
        self.cursor.execute(query, (idU,))
        result = self.cursor.fetchall()

        lista = [{"id_notificacion": row[0],
                    "id_contenido": row[1],
                    "title": row[2],
                    "messagge": row[3]} for row in result]
        return lista
    
    def obtenerListaNotificacionesRecargas(self, idU):
        query = """
                SELECT 
                    id,
                    id_contenido, 
                    messagge
                FROM 
                    notificaciones
                WHERE 
                    id_usuario = ? AND id_contenido = -1
            """
        self.cursor.execute(query, (idU,))
        result = self.cursor.fetchall()

        lista = [{"id_notificacion": row[0],
                    "id_contenido": row[1],
                    "title": 0,
                    "messagge": row[2]} for row in result]
        return lista
        
    def aceptarNotificacion(self, id_noti):
        query_delete = "DELETE FROM notificaciones WHERE id = ?"
        self.cursor.execute(query_delete, (id_noti,))
        self.conn.commit()
            
class E_Recargas:
    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def registrarSolicitud(self, monto, user_id):
        fecha = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        query = "INSERT INTO recargas (id_user, monto, fecha) VALUES (?, ?, ?)"
        self.cursor.execute(query, (user_id, monto, fecha))
        self.conn.commit()

    def obtenerListaPeticiones(self):
        query = """
            SELECT 
                recargas.id, 
                usuarios.username, 
                recargas.monto, 
                recargas.fecha, 
                recargas.estado
            FROM 
                recargas
            JOIN 
                usuarios ON recargas.id_user = usuarios.id
            WHERE 
                recargas.estado = 'pendiente' AND usuarios.estado_cuenta = 'cliente'
        """
        self.cursor.execute(query)
        result = self.cursor.fetchall()

        lista = [{"id_recarga": row[0],
                "usuario": row[1],
                "monto": row[2],
                "fecha": row[3],
                "estado": row[4]} for row in result]

        return lista
    
    def obtenerRecargasCliente(self, idU):
        query = """
            SELECT 
                id,
                monto,
                fecha,
                estado
            FROM 
                recargas
            WHERE 
                id_user = ?
        """
        self.cursor.execute(query,(idU))
        result = self.cursor.fetchall()

        lista = [{"id_recarga": row[0],
                "monto": row[1],
                "fecha": row[2],
                "estado": row[3]} for row in result]

        return lista
        
    def aprobarRecarga(self, id_recarga):
        query = "SELECT id_user, monto FROM recargas WHERE id = ? AND estado = 'pendiente'"
        self.cursor.execute(query, (id_recarga,))
        result = self.cursor.fetchone()
        if result:
            id_user, monto = result
            query_set = "UPDATE recargas SET estado = 'aprobada' WHERE id = ?"
            self.cursor.execute(query_set, (id_recarga,))
            self.conn.commit()
            return id_user, monto
        return None, None
    

class E_Contenidos:
    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()
        
    def registrarContenido(self, data):
        query = """
            INSERT INTO contenidos (
                src,
                title,
                author,
                price,
                extension,
                category,
                rating,
                description,
                type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.cursor.execute(query, (
            data["src"],
            data["title"],
            data["author"],
            float(data["price"]),
            data["extension"],
            data["category"],
            float(data["rating"]),
            data["description"],
            data["type"]
        ))
        self.conn.commit()

    def actualizarContenido(self, data):
        campos_validos = {
            "src": data.get("src"),
            "title": data.get("title"),
            "author": data.get("author"),
            "price": float(data["price"]) if data.get("price") is not None else None,
            "extension": data.get("extension"),
            "category": data.get("category"),
            "rating": float(data["rating"]) if data.get("rating") is not None else None,
            "description": data.get("description"),
            "type": data.get("type")
        }

        # Filtrar solo campos que no son None
        columnas = []
        valores = []

        for campo, valor in campos_validos.items():
            if valor is not None:
                columnas.append(f"{campo} = ?")
                valores.append(valor)

        if not columnas:
            return  # Nada que actualizar

        query = f"""
            UPDATE contenidos SET
                {', '.join(columnas)}
            WHERE id = ?
        """

        valores.append(data["id"])
        self.cursor.execute(query, tuple(valores))
        self.conn.commit()

    def obtenerContenidos(self, top=False):
        query = """
            SELECT id, src, title, author, price, description, rating, type, category, extension, downloaded
            FROM contenidos """
        if top:
            query += "ORDER BY downloaded DESC"

        self.cursor.execute(query)
        result = self.cursor.fetchall()
        lista = []
        for row in result:
            id_, src_bin, title, author, price, desc, rating, tipo, category, ext, down = row
            data_url = C_Contenidos._generar_data_url(src_bin, tipo, ext)
            lista.append({
                "id": id_,
                "src": data_url,
                "title": title,
                "author": author,
                "price": price,
                "description": desc,
                "rating": rating,
                "type": tipo,
                "category": category,
                "downloaded" : down
            })
        return lista

    def Buscar_info(self, query="", filters=None):
        if filters is None:
            filters = []

        sql = "SELECT id, title, author, type FROM contenidos WHERE 1=1"
        params = []

        tipos = [f.lower() for f in filters if f.lower() in ["imagen", "video", "audio"]]
        if tipos:
            placeholders = ", ".join(["?"] * len(tipos))
            sql += f" AND LOWER(type) IN ({placeholders})"
            params.extend(tipos)

        filters_lower = [f.lower() for f in filters]

        if query:
            if "id" in filters_lower:
                sql += " AND CAST(id AS TEXT) LIKE ?"
                params.append(f"%{query}%")
            else:
                if "author" in filters_lower:
                    sql += " AND LOWER(author) LIKE ?"
                    params.append(f"%{query.lower()}%")
                else:
                    sql += " AND (LOWER(title) LIKE ? OR CAST(id AS TEXT) LIKE ? OR LOWER(author) LIKE ?)"
                    params.extend([f"%{query.lower()}%", f"%{query.lower()}%", f"%{query.lower()}%"])

        self.cursor.execute(sql, params)
        result = self.cursor.fetchall()

        lista = []
        for row in result:
            lista.append({
                "id": row[0],
                "title": row[1],
                "author": row[2],
                "type": row[3],
            })
        return lista

    def getContent(self, content_id):
        query = "SELECT * FROM contenidos WHERE id = ?"
        self.cursor.execute(query, (content_id,))
        row = self.cursor.fetchone()
        if row:
            keys = [desc[0] for desc in self.cursor.description]
            content_dict = dict(zip(keys, row))

            # convertir binario a data URL
            content_dict["src"] = C_Contenidos._generar_data_url(
                content_dict["src"], content_dict["type"], content_dict["extension"]
            )
            return content_dict
        else:
            return None

    def obtenerPrecio(self, content_id):
        query = "SELECT price FROM contenidos WHERE id = ?"
        self.cursor.execute(query, (content_id,))
        return self.cursor.fetchone()[0]

    def verificarPromocion(self, idC):
        return 0*idC
    
    def obtenerBinarioPorID(self, idC):
        self.cursor.execute("SELECT src, title, extension FROM contenidos WHERE id = ?", (idC,))
        row = self.cursor.fetchone()
        if row:
            return {
                "src": row[0],  # binario
                "title": "_".join(row[1].split(" ")),
                "extension": row[2]  # etc.
            }
        return None
    
    def downloadCount(self, id):
        query = """
            UPDATE contenidos SET
               downloaded = downloaded + 1
            WHERE id = ?
        """
        self.cursor.execute(query, (id,))
        self.conn.commit()
        
class C_Puntuacion:
    def __init__(self):
        pass

    def Obtener_Puntuacion(self, idU, idC):
        e_pun = E_Puntuaciones()
        return e_pun.Existe_Puntuacion(idU, idC)
    
    def Enviar_Puntuacion(self, idU, idC, score):
       e_pun = E_Puntuaciones()
       e_pun.Registrar_Puntuacion(idU,idC,score)

class C_Transacciones:
    def __init__(self):
        pass
    def verificarMetPago(self, Ncard, cardType):
        generate_Bancos_disponibles = lambda a: a in ["mastercard","bcp","visa","paypal"]
        return generate_Bancos_disponibles(cardType)
    
    def realizarPago(self, user_id, amount, Ncard):
        pagoTarjeta = lambda a,b : 1
        if pagoTarjeta(amount, Ncard):
            controller = E_Recargas()
            controller.registrarSolicitud(amount, user_id)
            return 0
        return 1
    def obtenerListaPeticiones(self):
        controller = E_Recargas()
        return controller.obtenerListaPeticiones()
    
    def obtenerRecargasCliente(self, idU):
        controller = E_Recargas()
        return controller.obtenerRecargasCliente(idU)
        
    def aprobarRecarga(self, id_recarga):
        controller = E_Recargas()
        id_user, cantidad = controller.aprobarRecarga(id_recarga)
        return id_user, cantidad
    
    def ProcesarPrecioFinal(self, idC):
        return 1

    def actualizarSaldo(self, idU, precio):
        controller = E_Usuarios()
        controller.actualizarSaldo(idU, precio)

    def registrarCompra(self, idU, idC, precio, d_des=None):
        if d_des!=None:
            uscont = E_Transacciones()
            uscont.registrarCompra(idU,idC,precio,'compra')
        else:
            uscont = E_Regalos()
            uscont.registrarRegalo(idU,idC,precio,'regalo',d_des)

    def verificarContenido(self, idu, idc):
        us_trans = E_Transacciones()
        us_rega = E_Regalos()     
        if us_trans.verificarContenido(idu,idu) or us_rega.verificarContenidoDestinatario(idu,idc):
            return True
        return False
    
class C_Contenidos:
    def get_id(self):
        return 1
    def registrarContenido(self, data):
        contenidos = E_Contenidos()
        contenidos.registrarContenido(data)

    def actualizarContenido(self, data):
        contenidos = E_Contenidos()
        contenidos.actualizarContenido(data)

    def consultarDatos(self, query, filters):
        query = query.lower().strip()
        resultados = []

        contenidos = E_Contenidos()
        A =  contenidos.obtenerContenidos()


        aut = 0 
        if 'author' in filters:
            filters.remove('author')
            aut = 1

        for item in A:
            if len(filters)==0 or item["type"] in filters:
                titulo = item.get('title', '').lower()
                author = item.get('author', '').lower()
                if query in titulo or (aut and query in author):
                    resultados.append({
                        'title': titulo,
                        'author': author,
                        'type': item["type"],
                        'id': item["id"]
                    })

        return resultados
    
    def solicitar_info_contenido(self, query, filters):
        contenidos = E_Contenidos()
        return contenidos.Buscar_info(query,filters)
    
    @staticmethod
    def _generar_data_url(bin_data, tipo, extension):
        # Parte	Explicación:
        # data:	Esquema que indica que se trata de un Data URL.
        # image/png	Tipo MIME del contenido (imagen en formato PNG en este caso).
        # ;base64	Indica que los datos están codificados en Base64.
        # iVBORw0KGgoAAA...	Los datos binarios del archivo codificados en Base64.
        # data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA..."
        # <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA..." />        
        mime_types = {
            "imagen": f"image/{extension}",
            "audio": f"audio/{extension}",
            "video": f"video/{extension}"
        }
        mime_type = mime_types.get(tipo, "application/octet-stream")
        encoded = base64.b64encode(bin_data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    
    @staticmethod
    def getTopContent():
        contenidos = E_Contenidos()
        todos = contenidos.obtenerContenidos(top=True)

        top_imagenes = []
        top_audios = []
        top_videos = []

        for item in todos:
            tipo = item['type']
            if tipo == 'imagen' and len(top_imagenes) < 10:
                top_imagenes.append(item)
            elif tipo == 'audio' and len(top_audios) < 10:
                top_audios.append(item)
            elif tipo == 'video' and len(top_videos) < 10:
                top_videos.append(item)

            # Si ya tienes 10 de cada tipo, puedes salir del bucle
            if len(top_imagenes) == 10 and len(top_audios) == 10 and len(top_videos) == 10:
                break

        return top_imagenes + top_audios + top_videos
    
    def getContent(self, content_id):
        contenidos = E_Contenidos()
        return contenidos.getContent(content_id)
    
    def obtenerPrecio(self, content_id):
        contenidos = E_Contenidos()
        return contenidos.obtenerPrecio(content_id)
    
    def verificarPromocion(self, idC):
        contenidos = E_Contenidos()
        return contenidos.verificarPromocion(idC)
    
    def Obtener_Puntuacion(self, idU, idC):
        c_pun = C_Puntuacion()
        return c_pun.Obtener_Puntuacion(idU, idC)
    
    def Enviar_Puntuacion(self, idU, idC, score):
       ctr = C_Puntuacion()
       ctr.Enviar_Puntuacion(idU,idC,score)

    def obtenerContenidoBinarios(self, idC):
        conte = E_Contenidos()
        contenido  = conte.obtenerBinarioPorID(idC)
        conte.downloadCount(idC)

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
            return mime_type, bin_data, filename
        return None,None,None
    
class C_Usuario:
    def __init__(self):
        self.id = None
    
    def getDataUser(self, id_user):
        usuarios = E_Usuarios()
        return usuarios.obtenerUser(id_user)

    def Buscar(self, query,filters):
        # content_manager = C_Contenidos()
        # return content_manager.consultarDatos(query,filters)
        content_manager = C_Contenidos()
        resultados = content_manager.solicitar_info_contenido(query, filters)
        return resultados
    
    def seleccionarContent(self, content_id):
        content_manager = C_Contenidos()
        return content_manager.getContent(content_id)
    
    def loginVerificar(self, username, password):
        usuarios = E_Usuarios()
        return usuarios.verificarLogin(username,password)
    
    def getContentView(self):
        content_manager = C_Contenidos()
        return content_manager.getContentView()

    def validarRegistro(self, user):
        us = E_Usuarios()
        return us.validarDatos(user)

    def registrarUsuario(self, user,ps,em):
        us = E_Usuarios()
        us.registrarUsuario(user,ps,em)

    def verificarContenido(self, idU, idC):
        c_usContenido = C_Transacciones()
        content_manager = C_Contenidos()
        res = {'success':c_usContenido.verificarContenido(idU, idC), 
               'hasRated':content_manager.Obtener_Puntuacion(idU, idC)}
        return res
    def obtenerDescargasCliente(self, idU):
        uscont = E_Transacciones()
        return uscont.obtenerDescargasCliente(idU)
    
    def obtenerRecargasCliente(self, idU):
        controller_trans = C_Transacciones()
        return controller_trans.obtenerRecargasCliente(idU)
    
    def obtenerContenidoDescarga(self,content_id):
        controller = C_Contenidos()
        return controller.obtenerContenidoBinarios(content_id) 

class C_Cliente(C_Usuario):
    def __init__(self):
        super().__init__()

    def enviarSolicitud(self, Ncard, amount, cardType, id_user):
        controller = C_Transacciones()
        if not controller.verificarMetPago(Ncard,cardType):
            return {"success": False, "message":"Metodo de pago invalido"}
        if controller.realizarPago(id_user, amount, Ncard):
            return {"success": False, "message":"Saldo insuficiente"}
        return {"success": True}
    
    def obtenerSaldo(self, id_user):
        usuarios = E_Usuarios()
        return usuarios.obtenerSaldo(id_user)

    def pagarContenido(self, idU, idC, id_des=None):
        controller_trans = C_Transacciones()
        controller_cont = C_Contenidos()
        saldo = self.obtenerSaldo(idU) 

        if controller_cont.verificarPromocion(idC):
            precioFinal = controller_trans.ProcesarPrecioFinal(idC)
        else:
            precioFinal = controller_cont.obtenerPrecio(idC)
            print(precioFinal)

        if saldo > precioFinal:
            controller_trans.actualizarSaldo(idU, -precioFinal)
        else:
            return False
        if id_des == None:
            controller_trans.registrarCompra(idU, idC, precioFinal)
        else:
            controller_trans.registrarCompra(idU, idC, precioFinal, id_des=id_des)
        return True
    
    def Obtener_Puntuacion(self, idU):
        ctr = C_Contenidos()
        return ctr.Obtener_Puntuacion(idU)
    
    def Enviar_Puntuacion(self, idU, idC, score):
       ctr = C_Contenidos()
       ctr.Enviar_Puntuacion(idU,idC,score)

    def Enviar_destinatario(self, idU, idC, destinatario):
        res = {'success':False}
        e_us = E_Usuarios()
        id_des = e_us.UsuarioExiste(destinatario, idU)
        if id_des==-1:
            res['msg']="El destinatario no existe."
        else:
            c_rega = C_Transacciones()
            if c_rega.verificarContenido(id_des, idC):
                res['msg'] = 'El destinatario ya tiene el contenido.'
            else:
                if not self.pagarContenido(idU, idC,id_des=id_des):
                    res['msg'] = 'Dinero insuficiente para la compra.'
                else:
                    res['success'] = True
                    e_notifi = E_Notificaciones()
                    from_user = e_us.obtenerUser(idU)['username']
                    e_notifi.registrarNotificacionRegalo(id_des, idC, f"Regalo de parte de {from_user}.")
        return res
    
    def SolicitarValidarSaldo(self, idU):
        if (self.obtenerSaldo(idU) == 0):
            usuarios = E_Usuarios()
            usuarios.registrar_Excliente(idU)
            return True
        return False
    
    def obtenerNotificaciones(self, idU):
        e_notifi = E_Notificaciones()
        res = e_notifi.obtenerListaNotificaciones(idU)
        res.extend(e_notifi.obtenerListaNotificacionesRecargas(idU))
        return res
    
    def aceptarNotificacion(self, idN):
        e_notifi = E_Notificaciones()
        e_notifi.aceptarNotificacion(idN)

    def Retirar_Saldo(self, card, cardType, idU):
        usuarios = E_Usuarios()
        monto = usuarios.obtenerSaldo(idU)
        controller_trans = C_Transacciones()
        #controller_trans.RegistrarRetiro(card, cardType, idU, monto)
        usuarios.actualizarSaldo(idU, -monto)
        return True
    
class C_Administrador(C_Usuario):
    def __init__(self):
        super().__init__()

    def getRecargas(self, estado=1):
        controller = C_Transacciones()
        return controller.obtenerListaPeticiones()
    
    def aprobarRecarga(self, id_recarga):
        controller = C_Transacciones()
        id_user,cantidad = controller.aprobarRecarga(id_recarga)
        print(id_user,cantidad)
        usuarios = E_Usuarios()
        usuarios.actualizarSaldo(id_user, cantidad)
        e_noti = E_Notificaciones()
        e_noti.registrarNotificacionRecarga(id_user,f"Recarga de ${cantidad} aprobada.")

    def ingresarAgregarContenido(self, datos):
        content_manager = C_Contenidos()
        content_manager.registrarContenido(datos)

    def actualizarContenido(self, datos):
        content_manager = C_Contenidos()
        content_manager.actualizarContenido(datos)

    def buscar_info(self, data):
        resultados = []
        filters = data['filters']
        if 'cliente' not in filters:
            content_manager = C_Contenidos()
            resultados = content_manager.solicitar_info_contenido(data['query'], filters)
        if not ('audio' in filters or 'video' in filters or 'imagen' in filters or 'author' in filters):
            usuarios = E_Usuarios()
            resultados += usuarios.buscar_info_usuarios(data['query'])

        return resultados
    
    def seleccionarUser(self, id):
        usuarios = E_Usuarios()
        return usuarios.obtenerUser(id)

    
class Usuario:
    def __init__(self,user=None,id=None, ctr=C_Usuario()):
        self.user = user
        self.id = id
        self.controller = ctr
        
    def iniciar_sesion(self, username, password):
        auth, self.id = self.controller.loginVerificar(username,password)
        return auth
    
    def Buscar(self, query,filters):
        print(self.user, self.id)
        return self.controller.Buscar(query,filters)
    
    def seleccionar(self, content_id):
        return self.controller.seleccionarContent(content_id)
    
    def getDataUser(self):
        return self.controller.getDataUser(self.id)
    
    def registrarU(self, data):
        return 1
    
    def getContentView(self):
        return self.controller.getContentView()
    
    def validarRegistro(self, us, ps, em):
        if not self.controller.validarRegistro(us):
            return 0
        self.controller.registrarUsuario(us,ps,em)
        return 1
    
    def verificarContenido(self, idC):
        return self.controller.verificarContenido(self.id, idC)
    def aceptarNotificacion(self, idN):
        self.controller.aceptarNotificacion(idN)

    def obtenerContenidoDescarga(self,content_id):
        return self.controller.obtenerContenidoDescarga(content_id)
    
class Cliente(Usuario):
    def __init__(self, username, id):
        super().__init__(user=username,id=id,ctr=C_Cliente())
        self.saldo = None
        self.estado_cuenta = None

    def ingresarMontoSolicitar(self, Ncard, amount, cardType):
        return self.controller.enviarSolicitud(Ncard, amount, cardType, self.id)
    
    def getSaldo(self):
        return self.controller.obtenerSaldo(self.id)
    
    def pagarContenido(self, idC):
        return self.controller.pagarContenido(self.id, idC)
    def obtenerDescargasCliente(self):
        return self.controller.obtenerDescargasCliente(self.id)
    def Obtener_Puntuacion(self, idU):
        return self.controller.Obtener_Puntuacion(idU)
    def Enviar_Puntuacion(self, idC, score):
        try:
            self.controller.Enviar_Puntuacion(self.id,idC,score)
        except:
            return False
        return True
    
    def Enviar_destinatario(self, idC, destinatario):
        return self.controller.Enviar_destinatario(self.id, idC, destinatario)
    def obtenerNotificaciones(self):
        return self.controller.obtenerNotificaciones(self.id)
    
    def SolicitarValidarSaldo(self):
        return self.controller.SolicitarValidarSaldo(self.id)
    def Retirar_Saldo(self, card, cardType):
        return self.controller.Retirar_Saldo(card, cardType, self.id)
    
class Administrador(Usuario):
    def __init__(self, username, id):
        super().__init__(user=username,id=id,ctr=C_Administrador())

    def obtenerRecargas(self):
        return self.controller.getRecargas()
    
    def aprobarSaldoCliente(self, id_recarga):
        self.controller.aprobarRecarga(id_recarga)
    
    def ingresarAgregarContenido(self, datos):
        self.controller.ingresarAgregarContenido(datos)
    def actualizarContenido(self, datos):
        self.controller.actualizarContenido(datos)

    def buscar_info(self, data):
        return self.controller.buscar_info(data)
    
    def seleccionar_user(self, id):
        return self.controller.seleccionarUser(id)
    
    def obtenerDescargasCliente(self, idU):
        return self.controller.obtenerDescargasCliente(idU)
    
    def obtenerRecargasCliente(self, idU):
        return self.controller.obtenerRecargasCliente(idU)