import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import urllib.parse
import hashlib

# --- NOMBRE DEL PROYECTO ---
NOMBRE_PANEL = "Streaming Perú"

# --- CONEXIÓN Y CREACIÓN DE TABLAS ---
def conectar_db():
    return sqlite3.connect('streaming_control.db')

def crear_tablas():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            password TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nombre TEXT,
            whatsapp TEXT,
            plataforma TEXT,
            correo TEXT,
            pin TEXT,
            fecha_vencimiento TEXT,
            precio REAL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()

crear_tablas()

# --- FUNCIONES DE SEGURIDAD ---
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def verificar_usuario(usuario, password):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, password FROM usuarios WHERE usuario = ?', (usuario,))
    resultado = cursor.fetchone()
    conn.close()
    if resultado and resultado[1] == hash_password(password):
        return resultado[0]
    return None

def registrar_usuario(usuario, password):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO usuarios (usuario, password) VALUES (?, ?)', (usuario, hash_password(password)))
        conn.commit()
        exito = True
    except sqlite3.IntegrityError:
        exito = False
    conn.close()
    return exito

# --- CONFIGURACIÓN ---
st.set_page_config(page_title=NOMBRE_PANEL, page_icon="🎬", layout="wide")

if 'conectado' not in st.session_state:
    st.session_state['conectado'] = False
if 'usuario_id' not in st.session_state:
    st.session_state['usuario_id'] = None
if 'usuario_nombre' not in st.session_state:
    st.session_state['usuario_nombre'] = ""

# --- LOGIN ---
if not st.session_state['conectado']:
    st.title(f"🎬 {NOMBRE_PANEL}")
    pestana = st.radio("Selecciona una opción", ["Iniciar Sesión", "Crear Cuenta Nueva"], horizontal=True)
    usuario_input = st.text_input("Nombre de Usuario").strip()
    password_input = st.text_input("Contraseña", type="password")
    
    if pestana == "Iniciar Sesión":
        if st.button("Ingresar al Panel"):
            u_id = verificar_usuario(usuario_input, password_input)
            if u_id:
                st.session_state['conectado'] = True
                st.session_state['usuario_id'] = u_id
                st.session_state['usuario_nombre'] = usuario_input
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    elif pestana == "Crear Cuenta Nueva":
        if st.button("Registrar Cuenta"):
            if usuario_input and password_input:
                if registrar_usuario(usuario_input, password_input):
                    st.success("Cuenta creada. Ya puedes iniciar sesión.")
                else:
                    st.error("Usuario en uso.")

# --- PANEL PRINCIPAL ---
else:
    col_logo, col_titulo = st.columns([1, 8])
    
    with col_logo:
        st.image("logo.png", width=70)
    with col_titulo:
        st.title(NOMBRE_PANEL)
        
    st.subheader(f"👋 Panel de: {st.session_state['usuario_nombre']}")
    
    if st.button("🚪 Cerrar Sesión"):
        st.session_state['conectado'] = False
        st.rerun()
        
    st.markdown("---")
    
    with st.sidebar:
        st.header("Registrar Cliente")
        nombre = st.text_input("Nombre del Cliente")
        whatsapp = st.text_input("WhatsApp / Teléfono")
        plataforma = st.selectbox("Plataforma", ["Netflix", "Disney+", "Max", "Prime Video", "Paramount+", "Magis TV", "IPTV", "Otro"])
        correo = st.text_input("Correo de la Cuenta")
        pin = st.text_input("Perfil / PIN")
        fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=date.today())
        precio = st.number_input("Precio Cobrado (S/.)", min_value=0.0, step=1.0)
        
        if st.button("Guardar Cliente"):
            if nombre and whatsapp:
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO clientes (usuario_id, nombre, whatsapp, plataforma, correo, pin, fecha_vencimiento, precio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (st.session_state['usuario_id'], nombre, whatsapp, plataforma, correo, pin, str(fecha_vencimiento), precio))
                conn.commit()
                conn.close()
                st.success("¡Guardado!")
                st.rerun()

    conn = conectar_db()
    df = pd.read_sql_query("SELECT * FROM clientes WHERE usuario_id = ?", conn, params=[st.session_state['usuario_id']])
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
