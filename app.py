import math
import os
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
    DATABASE=str(BASE / 'instance' / 'nutricion.db'),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=16384,
)

ACTIVIDADES = {
    'sedentaria': ('Sedentaria · poco o ningún ejercicio', 1.2),
    'ligera': ('Ligera · ejercicio 1 a 3 días por semana', 1.375),
    'moderada': ('Moderada · ejercicio 3 a 5 días por semana', 1.55),
    'alta': ('Alta · ejercicio 6 a 7 días por semana', 1.725),
}
OBJETIVOS = {
    'bajar': ('Bajar de peso', 0.9),
    'mantener': ('Mantener mi peso', 1.0),
    'subir': ('Subir de peso', 1.1),
}


def conectar():
    conexion = sqlite3.connect(app.config['DATABASE'])
    conexion.row_factory = sqlite3.Row
    conexion.execute('PRAGMA foreign_keys = ON')
    return conexion


def iniciar_db():
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    with closing(conectar()) as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                clave_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS calculos (
                id INTEGER PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                fecha TEXT NOT NULL DEFAULT (datetime('now')),
                edad INTEGER NOT NULL,
                sexo TEXT NOT NULL,
                altura REAL NOT NULL,
                peso REAL NOT NULL,
                actividad TEXT NOT NULL,
                objetivo TEXT NOT NULL,
                calorias INTEGER NOT NULL,
                proteinas REAL NOT NULL,
                carbohidratos REAL NOT NULL,
                grasas REAL NOT NULL
            );
        ''')


def db():
    if 'db' not in g:
        g.db = conectar()
    return g.db


@app.teardown_appcontext
def cerrar_db(error):
    conexion = g.pop('db', None)
    if conexion is not None:
        conexion.close()


@app.before_request
def preparar_peticion():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(24)
    if request.method == 'POST':
        token = request.form.get('csrf', '')
        if not secrets.compare_digest(token, session['csrf']):
            abort(400, 'El formulario venció. Recargá la página e intentá de nuevo.')


@app.after_request
def privacidad(respuesta):
    respuesta.headers['Cache-Control'] = 'no-store'
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    respuesta.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return respuesta


@app.context_processor
def datos_comunes():
    return dict(actividades=ACTIVIDADES, objetivos=OBJETIVOS,
                tablero_url=os.environ.get('TABLERO_URL', 'http://localhost:8501'))


def validar_calculo(datos):
    valores = {}
    limites = {'edad': (18, 78), 'altura': (120, 230), 'peso': (35, 250)}
    for campo, (minimo, maximo) in limites.items():
        try:
            valor = float(datos.get(campo, '').replace(',', '.'))
        except (ValueError, TypeError, AttributeError):
            raise ValueError(f'Ingresá un valor numérico en {campo}.')
        if not math.isfinite(valor) or not minimo <= valor <= maximo:
            raise ValueError(f'El campo {campo} debe estar entre {minimo} y {maximo}.')
        if campo == 'edad' and not valor.is_integer():
            raise ValueError('La edad debe ser un número entero.')
        valores[campo] = int(valor) if campo == 'edad' else valor
    for campo, opciones in [('sexo', ('femenino', 'masculino')),
                            ('actividad', ACTIVIDADES), ('objetivo', OBJETIVOS)]:
        if datos.get(campo) not in opciones:
            raise ValueError(f'Seleccioná una opción válida en {campo}.')
        valores[campo] = datos[campo]
    return valores


def calcular(datos):
    # Mifflin-St Jeor: peso en kg, altura en cm y edad en años.
    ajuste = 5 if datos['sexo'] == 'masculino' else -161
    basal = 10 * datos['peso'] + 6.25 * datos['altura'] - 5 * datos['edad'] + ajuste
    mantenimiento = basal * ACTIVIDADES[datos['actividad']][1]
    calorias = round(mantenimiento * OBJETIVOS[datos['objetivo']][1])
    # Reparto fijo del proyecto: 20% proteínas, 50% carbohidratos, 30% grasas.
    return dict(calorias=calorias, proteinas=round(calorias * 0.2 / 4, 1),
                carbohidratos=round(calorias * 0.5 / 4, 1),
                grasas=round(calorias * 0.3 / 9, 1))


@app.route('/')
def inicio():
    return render_template('inicio.html', titulo='Tu nutrición, en números')


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    error = None
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        clave = request.form.get('clave', '')
        if not 2 <= len(nombre) <= 60:
            error = 'El nombre debe tener entre 2 y 60 caracteres.'
        elif len(email) > 120 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            error = 'Ingresá un correo electrónico válido.'
        elif not 8 <= len(clave) <= 128:
            error = 'La contraseña debe tener entre 8 y 128 caracteres.'
        else:
            try:
                db().execute('INSERT INTO usuarios(nombre, email, clave_hash) VALUES (?, ?, ?)',
                             (nombre, email, generate_password_hash(clave)))
                db().commit()
                flash('Tu cuenta está lista. Ya podés ingresar.')
                return redirect(url_for('ingresar'))
            except sqlite3.IntegrityError:
                error = 'Ese correo ya está registrado.'
    return render_template('cuenta.html', titulo='Crear cuenta', registro=True, error=error), 400 if error else 200


@app.route('/ingresar', methods=['GET', 'POST'])
def ingresar():
    error = None
    if request.method == 'POST':
        usuario = db().execute('SELECT * FROM usuarios WHERE email = ?',
                              (request.form.get('email', '').strip().lower(),)).fetchone()
        if usuario and check_password_hash(usuario['clave_hash'], request.form.get('clave', '')):
            session.clear()
            session.update(usuario_id=usuario['id'], nombre=usuario['nombre'],
                           csrf=secrets.token_hex(24))
            session.permanent = True
            return redirect(url_for('calculadora'))
        error = 'El correo o la contraseña no son correctos.'
    return render_template('cuenta.html', titulo='Ingresar', registro=False, error=error), 400 if error else 200


@app.post('/salir')
def salir():
    session.clear()
    return redirect(url_for('inicio'))


@app.route('/calculadora', methods=['GET', 'POST'])
def calculadora():
    resultado, error = None, None
    if request.method == 'POST':
        try:
            datos = validar_calculo(request.form)
            resultado = calcular(datos)
            if session.get('usuario_id'):
                fila = dict(usuario_id=session['usuario_id'], **datos, **resultado)
                columnas = ', '.join(fila)
                parametros = ', '.join('?' for _ in fila)
                cursor = db().execute(f'INSERT INTO calculos ({columnas}) VALUES ({parametros})', tuple(fila.values()))
                db().commit()
                return redirect(url_for('resultado_guardado', calculo_id=cursor.lastrowid))
        except ValueError as e:
            error = str(e)
    return render_template('calculadora.html', titulo='Calculadora diaria',
                           resultado=resultado, error=error, datos=request.form), 400 if error else 200


@app.get('/resultado/<int:calculo_id>')
def resultado_guardado(calculo_id):
    if not session.get('usuario_id'):
        return redirect(url_for('ingresar'))
    fila = db().execute('SELECT * FROM calculos WHERE id = ? AND usuario_id = ?',
                        (calculo_id, session['usuario_id'])).fetchone()
    if fila is None:
        abort(404)
    return render_template('calculadora.html', titulo='Tu resultado diario',
                           resultado=fila, datos=dict(fila), guardado=True)


@app.get('/historial')
def historial():
    if not session.get('usuario_id'):
        return redirect(url_for('ingresar'))
    filas = db().execute('SELECT * FROM calculos WHERE usuario_id = ? ORDER BY id DESC',
                         (session['usuario_id'],)).fetchall()
    return render_template('historial.html', titulo='Mis cálculos', calculos=filas)


@app.get('/api/calculos')
def api_calculos():
    if not session.get('usuario_id'):
        return jsonify(error='Ingresá para consultar tus cálculos.'), 401
    filas = db().execute('SELECT * FROM calculos WHERE usuario_id = ? ORDER BY id',
                         (session['usuario_id'],)).fetchall()
    return jsonify(calculos=[dict(fila) for fila in filas])


@app.get('/api/csrf')
def api_csrf():
    # El tablero necesita el mismo token que usan los formularios del navegador.
    return jsonify(csrf=session['csrf'], conectado=bool(session.get('usuario_id')))


@app.route('/alimentos', methods=['GET', 'POST'])
def alimentos():
    producto, error = None, None
    codigo = request.form.get('codigo', '').strip()
    if request.method == 'POST':
        if not re.fullmatch(r'[0-9]{8,14}', codigo):
            error = 'Ingresá un código de barras de 8 a 14 dígitos.'
        else:
            try:
                respuesta = requests.get(
                    f'https://world.openfoodfacts.org/api/v2/product/{codigo}.json',
                    params={'fields': 'product_name,nutriments'},
                    headers={'User-Agent': 'NutriDiario/1.0 (educational nutrition calculator)'},
                    timeout=(3, 5))
                respuesta.raise_for_status()
                contenido = respuesta.json()
                if not isinstance(contenido, dict):
                    raise ValueError('Respuesta inválida')
                if contenido.get('status') == 0:
                    error = 'No encontramos ese alimento. Probá con otro código.'
                else:
                    item = contenido.get('product')
                    if not isinstance(item, dict) or not isinstance(item.get('nutriments'), dict):
                        raise ValueError('Faltan datos del producto')
                    nutrientes = item['nutriments']
                    producto = {'nombre': item.get('product_name') or 'Alimento sin nombre'}
                    for clave, externa in [('calorias', 'energy-kcal'), ('proteinas', 'proteins'),
                                            ('carbohidratos', 'carbohydrates'), ('grasas', 'fat')]:
                        valor = nutrientes.get(externa + '_100g')
                        producto[clave] = round(float(valor), 1) if valor is not None else None
                        if valor is not None and (not math.isfinite(producto[clave]) or producto[clave] < 0):
                            raise ValueError('Nutriente inválido')
            except (requests.RequestException, ValueError, TypeError, OverflowError):
                producto = None
                error = 'No pudimos consultar el servicio de alimentos. Intentá nuevamente más tarde.'
    return render_template('alimentos.html', titulo='Explorá tus alimentos',
                           producto=producto, error=error, codigo=codigo)


@app.get('/como-funciona')
def como_funciona():
    return render_template('metodo.html', titulo='Cómo se calcula')


iniciar_db()

if __name__ == '__main__':
    app.run(port=5000)
