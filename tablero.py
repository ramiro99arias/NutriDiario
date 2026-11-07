import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
URL = os.environ.get('FLASK_URL', 'http://127.0.0.1:5000').rstrip('/')
st.set_page_config(page_title='Mi tablero | NutriDiario', page_icon='🥗')
st.title('Mi tablero nutricional')
st.caption('Consultá las estimaciones que guardaste en NutriDiario.')

if 'cliente' not in st.session_state:
    st.session_state.cliente = requests.Session()
if 'conectado' not in st.session_state:
    st.session_state.conectado = False
cliente = st.session_state.cliente

if not st.session_state.conectado:
    with st.form('ingreso', clear_on_submit=True):
        st.write('Ingresá con la misma cuenta de la web.')
        correo = st.text_input('Correo electrónico')
        clave = st.text_input('Contraseña', type='password')
        enviar = st.form_submit_button('Ingresar')
    if enviar:
        try:
            token = cliente.get(URL + '/api/csrf', timeout=10)
            token.raise_for_status()
            respuesta = cliente.post(URL + '/ingresar', data={
                'email': correo, 'clave': clave, 'csrf': token.json()['csrf']},
                timeout=10, allow_redirects=False)
            if respuesta.status_code == 302:
                st.session_state.conectado = True
                st.rerun()
            else:
                st.error('No pudimos ingresar. Revisá el correo y la contraseña.')
        except (requests.RequestException, ValueError, KeyError):
            st.error('La web no está disponible. Intentá nuevamente más tarde.')
    st.stop()

if st.button('Cerrar sesión'):
    cliente.close()
    del st.session_state.cliente
    st.session_state.conectado = False
    st.rerun()

st.button('Actualizar datos')
try:
    respuesta = cliente.get(URL + '/api/calculos', timeout=10)
    if respuesta.status_code == 401:
        st.session_state.conectado = False
        st.rerun()
    respuesta.raise_for_status()
    datos = pd.DataFrame(respuesta.json()['calculos'])
except (requests.RequestException, ValueError, KeyError):
    st.error('No pudimos cargar los cálculos. La web puede estar temporalmente desconectada.')
    st.stop()

if datos.empty:
    st.info('Todavía no hay cálculos. Guardá una estimación desde la web para ver el tablero.')
    st.stop()

datos['fecha'] = pd.to_datetime(datos['fecha'], utc=True)
st.metric('Estimaciones guardadas', len(datos))
columna1, columna2 = st.columns(2)
columna1.metric('Última estimación', f"{datos.iloc[-1]['calorias']} kcal/día")
columna2.metric('Promedio de las estimaciones', f"{datos['calorias'].mean():.0f} kcal/día")
st.subheader('Calorías por cálculo')
serie = datos[['calorias']].copy()
serie.index = pd.Index(range(1, len(serie) + 1), name='Número de cálculo')
st.line_chart(serie)
st.subheader('Macronutrientes del último cálculo')
macros = datos.iloc[-1][['proteinas', 'carbohidratos', 'grasas']].astype(float)
macros.index = ['Proteínas', 'Carbohidratos', 'Grasas']
st.bar_chart(macros.rename('Gramos diarios'))
st.subheader('Historial (fechas en UTC)')
st.dataframe(datos[['fecha', 'objetivo', 'peso', 'calorias', 'proteinas', 'carbohidratos', 'grasas']], hide_index=True)
st.caption('Son estimaciones calculadas, no un registro de alimentos consumidos.')
