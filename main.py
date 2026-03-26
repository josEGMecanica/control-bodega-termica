import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN DE CONEXIÓN ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("llaves.json", scope)
    client = gspread.authorize(creds)
    return client.open("Inventario_Bodega") # Asegúrate que este sea el nombre real

sh = conectar_google_sheets()
inv_sh = sh.worksheet("Inventario")
mov_sh = sh.worksheet("Movimientos")

# --- 2. FUNCIONES DE LÓGICA ---

def actualizar_stock(nombre_item, cantidad, operacion="restar"):
    try:
        celda = inv_sh.find(nombre_item)
        fila = celda.row
        stock_actual = int(inv_sh.cell(fila, 4).value)
        nuevo_stock = stock_actual - cantidad if operacion == "restar" else stock_actual + cantidad
        inv_sh.update_cell(fila, 4, max(0, nuevo_stock))
        return True
    except: return False

# --- 3. INTERFAZ ---
st.set_page_config(page_title="Control de Bodega", page_icon="🛠️", layout="wide")

menu = st.sidebar.radio("Menú", ["📊 Dashboard / Inventario", "📤 Salida de Material", "📥 Devolución", "🆕 Registrar Nuevo Item"])

# --- SECCIÓN: DASHBOARD ---
if menu == "📊 Dashboard / Inventario":
    st.header("Inventario Actual")
    df_inv = pd.DataFrame(inv_sh.get_all_records())
    st.dataframe(df_inv, use_container_width=True)

# --- SECCIÓN: SALIDA (CON RESUMEN) ---
elif menu == "📤 Salida de Material":
    st.header("Registro de Salida")
    
    with st.form("form_salida"):
        # Ahora el nombre es libre para escribir
        trabajador = st.text_input("Nombre del Trabajador / Responsable")
        destino = st.text_input("Lugar de Destino")
        
        # Cargar materiales del inventario
        nombres_items = [row['Nombre'] for row in inv_sh.get_all_records()]
        seleccion = st.multiselect("¿Qué cosas se llevan?", nombres_items)
        cantidad = st.number_input("Cantidad de cada uno", min_value=1, value=1)
        
        enviar = st.form_submit_button("CONFIRMAR Y DESCONTAR")
        
        if enviar:
            if not trabajador or not seleccion:
                st.error("⚠️ Por favor escribe tu nombre y selecciona el material.")
            else:
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                for item in seleccion:
                    actualizar_stock(item, cantidad, "restar")
                
                # Guardar en Movimientos con estado PENDIENTE
                mov_sh.append_row([fecha, trabajador, destino, str(seleccion), "Salida", "PENDIENTE"])
                
                # RESUMEN PARA EL USUARIO
                st.success(f"✅ ¡Registro guardado exitosamente!")
                st.balloons()
                st.info(f"""
                **RESUMEN DE SALIDA:**
                * **Responsable:** {trabajador}
                * **Materiales:** {', '.join(seleccion)}
                * **Cantidad:** {cantidad} unidades c/u
                * **Fecha/Hora:** {fecha}
                """)

# --- SECCIÓN: DEVOLUCIÓN (CON FLECHITA) ---
elif menu == "📥 Devolución":
    st.header("Retorno de Equipo")
    data_mov = mov_sh.get_all_records()
    
    for i, mov in enumerate(data_mov):
        fila_excel = i + 2
        if mov.get('Estado_Retorno') == "PENDIENTE":
            with st.expander(f"📦 {mov['Trabajador']} - {mov['Items_Llevados']}"):
                if st.button("Confirmar Regreso ↩️", key=f"dev_{fila_excel}"):
                    # Lógica de devolución
                    items = mov['Items_Llevados'].replace("[", "").replace("]", "").replace("'", "").split(", ")
                    for it in items:
                        actualizar_stock(it.strip(), 1, "sumar")
                    mov_sh.update_cell(fila_excel, 6, "DEVUELTO")
                    st.rerun()

# --- SECCIÓN: REGISTRAR NUEVO MATERIAL ---
elif menu == "🆕 Registrar Nuevo Item":
    st.header("Alta de Nuevo Material o Herramienta")
    with st.form("nuevo_item"):
        nuevo_id = st.text_input("ID del Producto (Ej: HER-05)")
        nuevo_nombre = st.text_input("Nombre del Producto (Ej: Taladro Percutor)")
        nuevo_tipo = st.selectbox("Categoría", ["Herramienta", "Material", "Consumible"])
        nuevo_stock = st.number_input("Stock Inicial", min_value=0, value=0)
        nueva_unidad = st.selectbox("Unidad", ["Pieza", "Metros", "Litros", "Juego"])
        
        btn_crear = st.form_submit_button("AGREGAR AL INVENTARIO")
        
        if btn_crear:
            if nuevo_id and nuevo_nombre:
                inv_sh.append_row([nuevo_id, nuevo_nombre, nuevo_tipo, nuevo_stock, nueva_unidad])
                st.success(f"✨ '{nuevo_nombre}' ha sido agregado al inventario del Excel.")
            else:
                st.warning("Escribe el ID y el Nombre para continuar.")