import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import urllib.parse # Para preparar el link de WhatsApp seguro

# --- NOMBRE DE TU NEGOCIO (Cámbialo aquí si deseas) ---
NOMBRE_PANEL = "ANGEL DE LA GUARDA"

# --- CONEXIÓN A BASE DE DATOS ---
def conectar_db():
    return sqlite3.connect('streaming_control.db')

def crear_tablas():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            telefono TEXT,
            plataforma TEXT,
            correo TEXT,
            perfil TEXT,
            vencimiento TEXT,
            precio REAL,
            pago TEXT
        )
    ''')
    conn.commit()
    conn.close()

crear_tablas()

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title=NOMBRE_PANEL, layout="wide")
st.title(f"🎬 {NOMBRE_PANEL}")

# --- MENÚ LATERAL: REGISTRO MANUAL ---
st.sidebar.header("倾 Registrar Cliente Manualmente")
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
        # Limpiar el teléfono por si ponen espacios o guiones
        num_limpio = "".join(filter(str.isdigit, telefono))
        if not num_limpio.startswith("51") and len(num_limpio) == 9:
            num_limpio = "51" + num_limpio # Agrega el código de Perú automáticamente si son 9 dígitos
            
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO clientes (nombre, telefono, plataforma, correo, perfil, vencimiento, precio, pago)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nombre, num_limpio, plataforma, correo, perfil, vencimiento.strftime("%Y-%m-%d"), precio, pago))
        conn.commit()
        conn.close()
        st.sidebar.success(f"✔️ {nombre} agregado con éxito.")
        st.rerun()
    else:
        st.sidebar.error("Por favor, llena Nombre, Correo y WhatsApp.")

# --- PROCESAMIENTO AUTOMÁTICO DE DATOS ---
conn = conectar_db()
df = pd.read_sql_query("SELECT * FROM clientes", conn)
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

    # --- INDICADORES AUTOMÁTICOS EN SOLES ---
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
    
    # Mostramos la tabla limpia en soles
    df_visual = df_filtrado.copy()
    df_visual['Precio (S/.)'] = df_visual['precio'].apply(lambda x: f"S/. {x:,.2f}")
    
    st.dataframe(
        df_visual[['id', 'nombre', 'plataforma', 'correo', 'perfil', 'vencimiento', 'Días Restantes', 'Estado', 'pago', 'Precio (S/.)', 'telefono']],
        use_container_width=True
    )

    # --- SECCIÓN DE ACCIONES Y WHATSAPP DIRECTO ---
    st.markdown("---")
    st.subheader("⚙️ Conexión Directa y Acciones Rápidas")
    
    col_accion1, col_accion2 = st.columns(2)
    
    with col_accion1:
        st.markdown("**📱 Enviar Recordatorio de WhatsApp**")
        id_ws = st.number_input("Ingresa el ID del cliente para notificar:", min_value=1, step=1, key="id_whatsapp")
        
        # Buscar datos del cliente seleccionado para el mensaje
        cliente_sel = df[df['id'] == id_ws]
        
        if not cliente_sel.empty:
            c_nombre = cliente_sel['nombre'].values[0]
            c_tel = cliente_sel['telefono'].values[0]
            c_plat = cliente_sel['plataforma'].values[0]
            c_dias = cliente_sel['Días Restantes'].values[0]
            
            # Crear el texto del mensaje automático
            if c_dias < 0:
                msg = f"Hola {c_nombre}, te saludamos de {NOMBRE_PANEL}. Te informamos que tu pantalla de {c_plat} ya venció. Quedamos atentos para ayudarte con tu renovación. ¡Muchas gracias!"
            elif c_dias <= 3:
                msg = f"Hola {c_nombre}, te saludamos de {NOMBRE_PANEL}. Te recordamos que a tu pantalla de {c_plat} le quedan {c_dias} días para vencer. Avísanos para proceder con la renovación y no te quedes sin servicio. ¡Gracias!"
            else:
                msg = f"Hola {c_nombre}, te saludamos de {NOMBRE_PANEL}. Tu servicio de {c_plat} está activo y le quedan {c_dias} días. ¡Que tengas un excelente día!"
                
            # Codificar el texto para que sea compatible con un enlace web
            msg_codificado = urllib.parse.quote(msg)
            link_whatsapp = f"https://wa.me/{c_tel}?text={msg_codificado}"
            
            # Botón web para abrir WhatsApp
            st.link_button(f"✉️ Enviar WhatsApp a {c_nombre}", link_whatsapp, type="secondary")
        else:
            st.caption("Introduce un ID válido de la tabla de arriba para generar el botón de envío.")

    with col_accion2:
        st.markdown("**🗑️ Eliminar Cliente del Sistema**")
        id_borrar = st.number_input("Ingresa el ID del cliente a eliminar:", min_value=1, step=1, key="id_eliminar")
        btn_borrar = st.button("🗑️ Eliminar Definitivamente", type="primary")
        
    if btn_borrar:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM clientes WHERE id = ?", (id_borrar,))
        resultado = cursor.fetchone()
        
        if resultado:
            cursor.execute("DELETE FROM clientes WHERE id = ?", (id_borrar,))
            conn.commit()
            st.success(f"Cliente '{resultado[0]}' eliminado.")
            conn.close()
            st.rerun()
        else:
            st.error("Ese ID de cliente no existe.")
            conn.close()
else:
    st.info(f"👋 ¡Bienvenido a {NOMBRE_PANEL}! Registra tu primer cliente en el menú de la izquierda.")