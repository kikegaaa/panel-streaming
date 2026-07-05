import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import urllib.parse
import hashlib

# --- NOMBRE DEL PROYECTO ---
NOMBRE_PANEL = "Streaming Center Perú 🇵🇪"

# --- CONEXIÓN Y CREACIÓN DE TABLAS ---
def conectar_db():
    return sqlite3.connect('streaming_control.db')

def crear_tablas():
    conn = conectar_db()
    cursor = conn.cursor()
    # Tabla para los usuarios del panel (Login)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            password TEXT
        )
    ''')
    # Tabla de clientes amarrada al id del usuario dueño
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nombre TEXT,
            telefono TEXT,
            plataforma TEXT,
            correo TEXT,
            perfil TEXT,
            vencimiento TEXT,
            precio REAL,
            pago TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()

crear_tablas()

# --- FUNCIONES DE SEGURIDAD (ENCRIPTA LAS CONTRASEÑAS) ---
def encriptar_pass(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def registrar_usuario(usuario, password):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (usuario, password) VALUES (?, ?)", (usuario, encriptar_pass(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verificar_usuario(usuario, password):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE usuario = ? AND password = ?", (usuario, encriptar_pass(password)))
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else None

# --- CONTROL DE SESIÓN ---
if 'usuario_id' not in st.session_state:
    st.session_state['usuario_id'] = None
if 'usuario_nombre' not in st.session_state:
    st.session_state['usuario_nombre'] = None

st.set_page_config(page_title=NOMBRE_PANEL, layout="wide")

# --- PANTALLA DE LOGIN / REGISTRO ---
if st.session_state['usuario_id'] is None:
    st.title(f"🎬 Bienvenido a {NOMBRE_PANEL}")
    
    pestana = st.radio("Selecciona una opción:", ["Iniciar Sesión", "Crear una Cuenta Nueva (Gratis)"], horizontal=True)
    
    with st.form("form_auth"):
        user_input = st.text_input("Nombre de Usuario").strip().lower()
        pass_input = st.text_input("Contraseña", type="password")
        btn_auth = st.form_submit_button("Confirmar")
        
    if btn_auth:
        if user_input and pass_input:
            if pestana == "Iniciar Sesión":
                u_id = verificar_usuario(user_input, pass_input)
                if u_id:
                    st.session_state['usuario_id'] = u_id
                    st.session_state['usuario_nombre'] = user_input
                    st.success(f"¡Bienvenido, {user_input}!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
            else:
                if registrar_usuario(user_input, pass_input):
                    st.success("¡Cuenta creada con éxito! Ya puedes cambiar a 'Iniciar Sesión'.")
                else:
                    st.error("Ese nombre de usuario ya está ocupado. Intenta con otro.")
        else:
            st.error("Por favor completa todos los campos.")
            
    st.stop() # Frena el código aquí si no han iniciado sesión

# --- SI LOGUEA CON ÉXITO, MUESTRA SU PANEL PRIVADO ---
st.title(f"🎬 {NOMBRE_PANEL}")
st.subheader(f"👋 Panel de: {st.session_state['usuario_nombre'].capitalize()}")

if st.button("🚪 Cerrar Sesión"):
    st.session_state['usuario_id'] = None
    st.session_state['usuario_nombre'] = None
    st.rerun()

# --- MENÚ LATERAL: REGISTRO DE CLIENTES ---
st.sidebar.header("📝 Registrar Cliente Manualmente")
with st.sidebar.form("form_registro", clear_on_submit=True):
    nombre = st.text_input("Nombre del Cliente")
    telefono = st.text_input("WhatsApp / Teléfono (Ej: 987654321)")
    plataforma = st.selectbox("Plataforma", ["Netflix", "Disney+", "Max", "Prime Video", "Spotify", "Magis TV", "Crunchyroll", "Otro"])
    correo = st.text_input("Correo de la Cuenta")
    perfil = st.text_input("Perfil / PIN asignado")
    vencimiento = st.date_input("Fecha de Vencimiento", value=date.today())
    precio = st.number_input("Precio Cobrado (S/.)", min_value=0.0, step=5.0)
    pago = st.selectbox("¿Ya pagó?", ["Pagado", "Pendiente"])
    
    guardar = st.form_submit_button("Agregar a la Lista")

if guardar:
    if nombre and correo and telefono:
        num_limpio = "".join(filter(str.isdigit, telefono))
        if not num_limpio.startswith("51") and len(num_limpio) == 9:
            num_limpio = "51" + num_limpio # Agrega código de Perú automáticamente si son 9 dígitos
            
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO clientes (usuario_id, nombre, telefono, plataforma, correo, perfil, vencimiento, precio, pago)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (st.session_state['usuario_id'], nombre, num_limpio, plataforma, correo, perfil, vencimiento.strftime("%Y-%m-%d"), precio, pago))
        conn.commit()
        conn.close()
        st.sidebar.success(f"✔️ {nombre} agregado con éxito.")
        st.rerun()
    else:
        st.sidebar.error("Por favor, llena Nombre, Correo y WhatsApp.")

# --- CARGAR Y FILTRAR DATOS EXCLUSIVOS DEL USUARIO ---
conn = conectar_db()
df = pd.read_sql_query("SELECT * FROM clientes WHERE usuario_id = ?", conn, params=(st.session_state['usuario_id'],))
conn.close()

if not df.empty:
    hoy = datetime.now().date()
    
    def calcular_restantes(fecha_str):
        f_venc = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        return (f_venc - hoy).days

    df['Días Restantes'] = df['vencimiento'].apply(calcular_restantes)

    def estado_semaforo(dias):
        if dias < 0: return "❌ Vencido"
        elif dias <= 3: return "⚠️ Por Vencer"
        return "✅ Activo"

    df['Estado'] = df['Días Restantes'].apply(estado_semaforo)

    # --- INDICADORES EN SOLES ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Clientes Activos", len(df[df['Estado'] != "❌ Vencido"]))
    
    ganancias = df[df['pago'] == 'Pagado']['precio'].sum()
    col2.metric("Dinero Recaudado", f"S/. {ganancias:,.2f}")
    
    alertas = len(df[df['Días Restantes'] <= 3])
    col3.metric("Clientes en Alerta ⚠️", alertas)

    # --- TABLA DE CONTROL ---
    st.subheader("📋 Lista de Clientes")
    
    filtro = st.selectbox("Filtrar por Estado:", ["Todos", "✅ Activo", "⚠️ Por Vencer", "❌ Vencido"])
    df_filtrado = df if filtro == "Todos" else df[df['Estado'] == filtro]
    
    df_visual = df_filtrado.copy()
    df_visual['Precio (S/.)'] = df_visual['precio'].apply(lambda x: f"S/. {x:,.2f}")
    
    st.dataframe(
        df_visual[['id', 'nombre', 'plataforma', 'correo', 'perfil', 'vencimiento', 'Días Restantes', 'Estado', 'pago', 'Precio (S/.)', 'telefono']],
        use_container_width=True
    )

    # --- ACCIONES RÁPIDAS Y WHATSAPP ---
    st.markdown("---")
    st.subheader("⚙️ Conexión Directa y Acciones Rápidas")
    col_accion1, col_accion2 = st.columns(2)
    
    with col_accion1:
        st.markdown("**📱 Enviar Recordatorio de WhatsApp**")
        id_ws = st.number_input("Ingresa el ID del cliente para notificar:", min_value=1, step=1, key="id_whatsapp")
        cliente_sel = df[df['id'] == id_ws]
        
        if not cliente_sel.empty:
            c_nombre = cliente_sel['nombre'].values[0]
            c_tel = cliente_sel['telefono'].values[0]
            c_plat = cliente_sel['plataforma'].values[0]
            c_dias = cliente_sel['Días Restantes'].values[0]
            
            if c_dias < 0:
                msg = f"Hola {c_nombre}, te saludamos de {NOMBRE_PANEL}. Te informamos que tu pantalla de {c_plat} ya venció. Quedamos atentos para ayudarte con tu renovación. ¡Muchas gracias!"
            elif c_dias <= 3:
                msg = f"Hola {c_nombre}, te saludamos de {NOMBRE_PANEL}. Te recordamos que a tu pantalla de {c_plat} le quedan {c_dias} días para vencer. Avísanos para proceder con la renovación y no quedarte sin servicio. ¡Gracias!"
            else:
                msg = f"Hola {c_nombre}, te saludamos de {NOMBRE_PANEL}. Tu servicio de {c_plat} está activo y le quedan {c_dias} días. ¡Que tengas un excelente día!"
                
            msg_codificado = urllib.parse.quote(msg)
            link_whatsapp = f"https://wa.me/{c_tel}?text={msg_codificado}"
            st.link_button(f"✉️ Enviar WhatsApp a {c_nombre}", link_whatsapp)
        else:
            st.caption("Introduce un ID válido de tu lista de arriba.")

    with col_accion2:
        st.markdown("**🗑️ Eliminar Cliente del Sistema**")
        id_borrar = st.number_input("Ingresa el ID del cliente a eliminar:", min_value=1, step=1, key="id_eliminar")
        btn_borrar = st.button("🗑️ Eliminar Definitivamente", type="primary")
        
    if btn_borrar:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM clientes WHERE id = ? AND usuario_id = ?", (id_borrar, st.session_state['usuario_id']))
        resultado = cursor.fetchone()
        
        if resultado:
            cursor.execute("DELETE FROM clientes WHERE id = ?", (id_borrar,))
            conn.commit()
            st.success(f"Cliente '{resultado[0]}' eliminado con éxito.")
            conn.close()
            st.rerun()
        else:
            st.error("Ese ID no te pertenece o no existe.")
            conn.close()
else:
    st.info("👋 ¡Tu panel está limpio! Comienza registrando tu primer cliente en el menú de la izquierda.")
