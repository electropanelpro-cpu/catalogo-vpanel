from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import os
import sys
import random
import threading

# --- INTEGRACIÓN DE VENTANA DE ESCRITORIO ---
try:
    import webview
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# ----------------------
# DETECTAR RUTA (Optimizado para Render y Local)
# ----------------------
base_path = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(base_path, 'templates'),
    static_folder=os.path.join(base_path, 'static')
)

app.secret_key = 'electropanel_secret_key'

# ----------------------
# FUNCIÓN PARA DETECTAR CELULAR
# ----------------------
def es_celular():
    ua = request.headers.get('User-Agent', '').lower()
    plataformas = ["android", "iphone", "ipad", "mobile", "windows phone", "nexus", "pixel"]
    return any(x in ua for x in plataformas)

# ----------------------
# CONFIGURACIÓN DE IA LOCAL
# ----------------------
CONOCIMIENTO_PANEL = {
    "normas": [
        "El CNE es la ley. La altura del tablero al eje de manijas debe ser 1.20m.",
        "Para ambientes industriales usa gabinetes IP65. La seguridad no se negocia.",
        "El código exige rotulado indeleble en todos los circuitos.",
        "Caída de tensión: no te pases del 3% en alimentadores.",
        "Usa barras de cobre siempre que pases de 100A.",
        "Deja al menos 1 metro libre al frente para mantenimiento.",
        "La puesta a tierra debe tener menos de 25 ohmios.",
        "Circuitos de iluminación y tomas deben ir por separado."
    ],
    "marcas": [
        "Schneider es el estándar de oro con la línea Acti9.",
        "Siemens es indestructible para control con su línea Sirius.",
        "ABB tiene interruptores de caja moldeada (MCCB) de alta tecnología.",
        "Evita componentes chinos genéricos; el breaker debe ser certificado.",
        "Usa canaletas ranuradas para un peinado de cables estético.",
        "Phoenix Contact para bornes de conexión seguros.",
        "Los variadores Altivar son excelentes para control de motores.",
        "Un diferencial de marca certificada es vital para salvar vidas."
    ],
    "automatizacion": [
        "Separa cables de control de potencia para evitar ruido eléctrico.",
        "Los variadores (VDF) requieren ventilación forzada con filtro.",
        "Usa relés de interfase para proteger las salidas del PLC.",
        "Las pantallas HMI deben ser intuitivas para el operador.",
        "Cable apantallado para señales 4-20mA siempre.",
        "Dominamos instrumentación inductiva y capacitiva.",
        "Comunicación Modbus TCP/IP para integraciones limpias.",
        "Deja un 20% de entradas y salidas (I/O) libres para el futuro."
    ],
    "fallas": [
        "Los puntos calientes por tornillos flojos causan incendios.",
        "El polvo metálico en tableros causa arcos eléctricos fatales.",
        "Las sobrecargas ocurren por añadir máquinas sin avisar.",
        "Un diferencial de calidad evita accidentes por falla a tierra.",
        "Los armónicos ensucian la red; usa filtros si tienes variadores.",
        "Si un breaker salta, investiga la instalación antes de reponer."
    ],
    "personalidad": [
        "¡Qué tal! Soy la IA de V-Panel. Hablemos de ingeniería real.",
        "Hola colega. Suéltame la duda técnica que tengas.",
        "Bienvenido. Vamos al grano con tu proyecto.",
        "¿Qué onda? Reportándome desde el núcleo de V-Panel.",
        "IA en línea. ¿Qué tablero estamos optimizando hoy?",
        "Saludos. Soy el experto local de ElectroPanel Pro."
    ],
    "default": [
        "Dame más datos técnicos. Aquí calculamos con precisión.",
        "Pregúntame por térmicos, PLC o normativas CNE.",
        "¿Es un tablero de distribución o transferencia automática?",
        "Necesito saber la carga nominal para responderte bien.",
        "En V-Panel priorizamos la eficiencia técnica.",
        "Hablemos de breakers o automatización industrial."
    ]
}

# ----------------------
# CONFIGURACIÓN DE CORREO
# ----------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'electropanelpro@gmail.com'
app.config['MAIL_PASSWORD'] = 'imydnufxtdmgmbms' 
app.config['MAIL_DEFAULT_SENDER'] = 'electropanelpro@gmail.com'

mail = Mail(app)

# ----------------------
# BASE DE DATOS
# ----------------------
db_path = os.path.join(base_path, 'vpanel_master.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----------------------
# MODELOS
# ----------------------
class Proyecto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100))
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(200))
    tension = db.Column(db.String(50), default="380V - 440V AC")
    ip = db.Column(db.String(50), default="IP65")
    material = db.Column(db.String(100), default="Acero LAF 1.5mm")
    entrega = db.Column(db.String(50), default="03-05 DÍAS")
    archivo_3d = db.Column(db.String(200), default="tablero1.glb")
    componentes_json = db.Column(db.JSON) 
    comentarios = db.relationship('Comentario', backref='proyecto', lazy=True, cascade="all, delete-orphan")

class Comentario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    texto = db.Column(db.Text)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'))

def crear_proyectos_iniciales():
    if Proyecto.query.count() == 0:
        comp_estandar = [
            {"nombre": "Gabinete Metálico", "cant": "1 ud."},
            {"nombre": "Interruptores Termom.", "cant": "3 ud."},
            {"nombre": "Borneras Conexión", "cant": "12 ud."}
        ]
        
        proyectos_data = [
            ("Tablero de distribución principal TDF-01", "Recepción y distribución segura de energía.", "tablero1.jpg", "380V", "IP65", "Acero LAF", "03-05 DÍAS", "tablero1.glb"),
            ("Tablero de distribución JUMBO", "Tablero de Distribución de Alta Capacidad - Jumbo Series.", "tablero2.jpg", "220V/24V", "IP54", "Acero LAF", "07-10 DÍAS", "tablero2.glb"),
            ("Tablero de distribución TD", "Este equipo garantiza una segregación de circuitos eficiente.", "tablero3.jpg", "440V", "IP65", "Acero LAF", "10-15 DÍAS", "tablero3.glb"),
            ("Tablero de Arranque Dol TBS-2", "El modelo TBS-2 ofrece una solución compacta y segura.", "tablero4.jpg", "380V", "IP65", "Acero LAF", "05-07 DÍAS", "tablero4.glb"),
            ("Tablero de Servicios Auxiliares", "Energía para iluminación y tomas auxiliares.", "tablero5.jpg", "220V", "IP40", "Acero LAF", "03 DÍAS", "tablero5.glb"),
            ("Tablero de Banco de Condensadores", "Compensación de reactiva y factor de potencia.", "tablero6.jpg", "440V", "IP54", "Acero LAF", "12-15 DÍAS", "tablero6.glb"),
            ("Caja de Control Local", "Mando y señalización local en campo.", "tablero7.jpg", "24V DC", "IP66", "Poliéster", "02-04 DÍAS", "tablero7.glb"),
            ("Tablero de Protección de Red", "Protección contra sobretensiones y fallas de fase.", "tablero8.jpg", "380V", "IP54", "Acero LAF", "04 DÍAS", "tablero8.glb"),
            ("Tablero de Alumbrado y Fuerza", "Control de luminarias y tomas industriales.", "tablero9.jpg", "220V", "IP54", "Acero LAF", "05 DÍAS", "tablero9.glb"),
            ("Tablero de Control de Bombas", "Presión constante con variadores de frecuencia.", "tablero10.jpg", "380V", "IP65", "Acero LAF", "08 DÍAS", "tablero10.glb"),
            ("Centro de Carga Residencial", "Distribución compacta con protección diferencial.", "tablero11.jpg", "220V", "IP20", "Resina", "02 DÍAS", "tablero11.glb"),
            ("Gabinete de Comunicaciones IT", "Cableado estructurado para red industrial.", "tablero12.jpg", "110V/220V", "IP20", "Acero", "05 DÍAS", "tablero12.glb"),
            ("Arranque Estrella-Triángulo", "Reducción de corriente de arranque en motores.", "tablero13.jpg", "440V", "IP54", "Acero LAF", "06 DÍAS", "tablero13.glb"),
            ("Monitoreo de Energía", "Analizadores de red para gestión de consumo.", "tablero14.jpg", "220V", "IP40", "Acero LAF", "05 DÍAS", "tablero14.glb"),
            ("Mando Neumático PLC", "Integración de electroválvulas y control de aire.", "tablero15.jpg", "24V DC", "IP65", "Acero LAF", "12 DÍAS", "tablero15.glb"),
            ("Celda de Media Tensión", "Diseño de protección para subestaciones.", "tablero16.jpg", "10KV/22.9KV", "IP54", "Acero Galvanizado", "25-30 DÍAS", "tablero16.glb"),
            ("Tablero de Transferencia Manual", "Selector de fuente de energía para respaldo.", "tablero17.jpg", "380V", "IP54", "Acero LAF", "03 DÍAS", "tablero17.glb"),
            ("Gabinete UPS Industrial", "Respaldo de energía crítica para servidores.", "tablero18.jpg", "220V", "IP20", "Acero LAF", "10 DÍAS", "tablero18.glb"),
            ("Tablero de Climatización HVAC", "Control de unidades de aire acondicionado central.", "tablero19.jpg", "380V", "IP54", "Acero LAF", "07 DÍAS", "tablero19.glb"),
            ("Caja de Paso de Potencia", "Derivación segura de alimentadores principales.", "tablero20.jpg", "1000V", "IP65", "Acero LAF", "03 DÍAS", "tablero20.glb"),
            ("Tablero de Rectificadores DC", "Conversión AC/DC para sistemas de telecomunicaciones.", "tablero21.jpg", "48V DC", "IP20", "Acero LAF", "15 DÍAS", "tablero21.glb"),
            ("Tablero de Alumbrado Público", "Control automático con fotoceldas y contactores.", "tablero22.jpg", "220V", "IP65", "Poliéster", "05 DÍAS", "tablero22.glb"),
            ("Centro de Medición Multifamiliar", "Concentración de medidores para edificios.", "tablero23.jpg", "220V", "IP43", "Acero LAF", "10 DÍAS", "tablero23.glb"),
            ("Tablero de Incendio (RCI)", "Alimentación para bombas contra incendio certificadas.", "tablero24.jpg", "380V", "IP65", "Rojo Epóxico", "12 DÍAS", "tablero24.glb"),
            ("Tablero de Ascensores", "Protección y control para sistemas de elevación vertical.", "tablero25.jpg", "380V", "IP54", "Acero LAF", "08 DÍAS", "tablero25.glb"),
            ("Gabinete de Variadores de Minería", "Control robusto para fajas transportadoras mineras.", "tablero26.jpg", "440V", "IP66", "Inox 304", "20 DÍAS", "tablero26.glb"),
            ("Tablero de Fuerza para Calderas", "Distribución eléctrica para sistemas térmicos industriales.", "tablero27.jpg", "380V", "IP54", "Acero LAF", "07 DÍAS", "tablero27.glb"),
            ("Módulo de Parada de Emergencia", "Sistema centralizado de seguridad funcional SIL-2.", "tablero28.jpg", "24V DC", "IP65", "Amarillo Seguridad", "05 DÍAS", "tablero28.glb"),
            ("Tablero de Data Center PDU", "Distribución de precisión para racks de servidores.", "tablero29.jpg", "220V", "IP20", "Acero LAF", "12 DÍAS", "tablero29.glb"),
            ("Tablero de Energía Solar (On-Grid)", "Sincronización de inversores con la red pública.", "tablero30.jpg", "380V", "IP65", "Aluminio", "10 DÍAS", "tablero30.glb"),
            ("Tablero de Laboratorio Químico", "Gabinete en acero inoxidable resistente a corrosión.", "tablero31.jpg", "220V", "IP67", "Inox 316L", "15 DÍAS", "tablero31.glb"),
            ("Caja de Distribución de Obra", "Tablero portátil reforzado para construcción.", "tablero32.jpg", "380V", "IP65", "Poliuretano", "04 DÍAS", "tablero32.glb"),
            ("Tablero de Ventilación Forzada", "Extracción de monóxido en sótanos y túneles.", "tablero33.jpg", "380V", "IP54", "Acero LAF", "08 DÍAS", "tablero33.glb"),
            ("Gabinete de Telemetría GPRS", "Monitoreo remoto de señales analógicas y digitales.", "tablero34.jpg", "12V/24V", "IP66", "Poliéster", "10 DÍAS", "tablero34.glb"),
            ("Tablero de Calefacción Industrial", "Control de las resistencias para hornos de secado.", "tablero35.jpg", "440V", "IP54", "Acero LAF", "12 DÍAS", "tablero35.glb"),
            ("Celda de Transformación Seca", "Protección térmica para transformadores de resina.", "tablero36.jpg", "10KV", "IP31", "Acero LAF", "20 DÍAS", "tablero36.glb"),
            ("Tablero de Control de Grúas", "Mando inalámbrico para puentes grúa industriales.", "tablero37.jpg", "440V", "IP65", "Acero LAF", "15 DÍAS", "tablero37.glb"),
            ("Módulo de Filtrado de Armónicos", "Mejora de la calidad de energía en redes sucias.", "tablero38.jpg", "380V", "IP54", "Acero LAF", "18 DÍAS", "tablero38.glb"),
            ("Tablero de Comando Hidráulico", "Gestión de electroválvulas para prensas de alta presión.", "tablero39.jpg", "24V/220V", "IP65", "Acero LAF", "14 DÍAS", "tablero39.glb"),
            ("Gabinete de Seguridad Perimetral", "Alimentación centralizada para sistemas de videovigilancia.", "tablero40.jpg", "220V", "IP54", "Acero LAF", "06 DÍAS", "tablero40.glb")
        ]

        for t, d, i, ten, ip_v, mat, ent, a3d in proyectos_data:
            db.session.add(Proyecto(
                titulo=t, descripcion=d, imagen=i,
                tension=ten, ip=ip_v, material=mat,
                entrega=ent, archivo_3d=a3d, componentes_json=comp_estandar
            ))
        db.session.commit()

# --- RUTAS SINCRONIZADAS ---

@app.route('/')
def inicio():
    return render_template('index_celular.html') if es_celular() else render_template('index.html')

@app.route('/servicios')
def servicios():
    return render_template('servicios_celular.html') if es_celular() else render_template('servicios.html')

@app.route('/proyectos')
def proyectos():
    try:
        db.create_all()
        crear_proyectos_iniciales()
        proyectos_data = Proyecto.query.all()
        if es_celular():
            return render_template('proyectos_celular.html', proyectos=proyectos_data)
        return render_template('proyectos.html', proyectos=proyectos_data)
    except Exception as e:
        return f"Error en base de datos: {str(e)}", 500

@app.route('/soporte')
def soporte():
    return render_template('soporte_celular.html') if es_celular() else render_template('soporte.html')

@app.route('/proyecto/<int:id>')
def ver_proyecto(id):
    try:
        db.create_all() # Asegura que la tabla existe antes de buscar
        proyecto = Proyecto.query.get(id)
        if not proyecto:
            crear_proyectos_iniciales()
            proyecto = Proyecto.query.get_or_404(id)
            
        if es_celular():
            return render_template('detalle_proyecto_celular.html', proyecto=proyecto)
        return render_template('detalle_proyecto.html', proyecto=proyecto)
    except Exception as e:
        # En lugar de 500, intentamos reparar y reintentar
        db.create_all()
        crear_proyectos_iniciales()
        return redirect(url_for('proyectos'))

@app.route('/proyecto/<int:id>/visor')
@app.route('/proyecto/<int:id>/visor-tecnico')
def visor3d(id):
    try:
        proyecto = Proyecto.query.get(id)
        if not proyecto:
            db.create_all()
            crear_proyectos_iniciales()
            proyecto = Proyecto.query.get_or_404(id)
            
        if es_celular():
            return render_template('visor_tecnico_celular.html', proyecto=proyecto)
        return render_template('visor3d.html', proyecto=proyecto)
    except Exception as e:
        return redirect(url_for('proyectos'))

@app.route('/descargar_plano/<int:id>')
@app.route('/descargar/<int:id>')
def descargar_plano(id):
    flash("Iniciando descarga de planos técnicos...", "success")
    return redirect(url_for('ver_proyecto', id=id))

@app.route('/preguntar', methods=['POST'])
def preguntar():
    data = request.get_json()
    msg = data.get("mensaje", "").lower()
    resp = random.choice(CONOCIMIENTO_PANEL["default"])
    if "hola" in msg: resp = random.choice(CONOCIMIENTO_PANEL["personalidad"])
    return jsonify({"respuesta": resp})

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        msg = Message(subject="COTIZACIÓN V-PANEL", recipients=['electropanelpro@gmail.com'], body=request.form.get('mensaje'))
        try: mail.send(msg)
        except: pass
        flash("Enviado", "success")
    return render_template('contacto_celular.html') if es_celular() else render_template('contacto.html')

@app.route('/comentar/<int:id>', methods=['POST'])
def comentar(id):
    try:
        nuevo = Comentario(nombre=request.form['nombre'], texto=request.form['texto'], proyecto_id=id)
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({"success": True, "nombre": nuevo.nombre, "texto": nuevo.texto})
    except:
        return jsonify({"success": False})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        crear_proyectos_iniciales()

    if not os.environ.get("RENDER") and GUI_AVAILABLE:
        threading.Thread(target=lambda: app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False), daemon=True).start()
        import time; time.sleep(1.5)
        webview.create_window('ElectroPanel Pro v2.0', 'http://127.0.0.1:5000/', width=1280, height=850)
        webview.start(private_mode=True)
    else:
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port)