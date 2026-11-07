# NutriDiario

Trabajo Práctico N.º 2 - Programación Web. Ramiro Arias y Clarisa Gariglio.

Aplicación sencilla para estimar calorías y macronutrientes diarios. Permite
registrarse, ingresar, guardar cálculos y consultar alimentos en Open Food Facts.
El tablero de Streamlit usa Pandas y consume el historial privado de la API Flask.

## Ejecutar en Windows

Desde esta carpeta, con Python 3.11 o posterior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; from pathlib import Path; p=Path('.env'); p.write_text(p.read_text().replace('SECRET_KEY=', 'SECRET_KEY='+secrets.token_hex(32), 1))"
.\.venv\Scripts\python.exe app.py
```

Abrir http://127.0.0.1:5000. Si el entorno y `.env` ya existen, ejecutar solamente
la última línea. No hace falta activar el entorno virtual.

En otra terminal, desde esta misma carpeta:

```powershell
.\.venv\Scripts\python.exe -m streamlit run tablero.py --server.address 127.0.0.1
```

Abrir http://localhost:8501 e ingresar con la misma cuenta. Primero registrar
la cuenta en Flask y guardar al menos un cálculo. Cada usuario ve solo sus datos.

## Archivos

- `app.py`: configuración, SQLite, validaciones, cálculo y rutas.
- `templates/`: plantillas que heredan de `base.html`.
- `static/`: CSS y JavaScript sin frameworks.
- `tablero.py`: tablero con Pandas y Streamlit, separado del servidor Flask.
- `requirements.txt`: dependencias compatibles.
- `PUBLICACION.md`: pasos para publicar Flask y el tablero.
- `informe.html`: informe de dos páginas preparado para imprimir en A4.
- `informe.pdf`: versión de dos páginas lista para leer; tiene señalados los datos pendientes.
- `comprobar.py`: seis pruebas funcionales con la biblioteca unittest de Python.

SQLite se crea automáticamente en `instance/nutricion.db`. No se entrega la base
con usuarios ni el entorno virtual ni `.env`. Las fechas se guardan en UTC.
Definir una `SECRET_KEY` estable evita que las sesiones se invaliden al reiniciar.
Sin esa variable la web funciona, pero genera una nueva clave en cada inicio.

## Cálculos

Mifflin-St Jeor: `10*peso + 6.25*altura - 5*edad + ajuste`.
Ajuste: +5 masculino, -161 femenino. Peso en kg, altura en cm.
Se multiplica por actividad (1.2, 1.375, 1.55 o 1.725) y objetivo (0.9, 1 o 1.1).
El ajuste del objetivo y los factores de actividad son aproximaciones del proyecto.
Reparto: 20% proteínas, 50% carbohidratos y 30% grasas; conversión a gramos: 4/4/9 kcal.
Adultos sanos de 18 a 78 años. No es una prescripción nutricional.
Fuentes y limitaciones visibles en `/como-funciona`.

## Recorrido para la demostración

1. Abrir inicio y calculadora; probar un campo vacío o fuera de rango.
2. Registrar una cuenta, ingresar y calcular con 30 años, masculino, 175 cm,
   70 kg, actividad moderada y objetivo mantener: 2556 kcal, 127.8 g de proteínas,
   319.5 g de carbohidratos y 85.2 g de grasas.
3. Ver el historial, reiniciar Flask y comprobar que el registro sigue guardado.
4. Usar «Ver mis datos en JSON» para consumir `/api/calculos` con fetch.
5. Consultar el código `3017620422003` en Alimentos. Si el servicio no responde,
   se muestra un error sin interrumpir la calculadora. No se inventan valores faltantes.
6. Ingresar al tablero y mostrar los gráficos con los cálculos de esa cuenta.
7. Salir e ingresar con otra cuenta para comprobar la separación de historiales.

## Correspondencia con la consigna

| Requisito | Implementación |
| --- | --- |
| Flask, entorno y dependencias | app.py, .venv local, requirements.txt |
| Cuatro rutas o más y herencia Jinja2 | Inicio, calculadora, registro, ingreso, historial, alimentos y método |
| Validación cliente y servidor | Restricciones HTML, JavaScript y validaciones Python |
| SQLite persistente | Usuarios y cálculos en instance/nutricion.db |
| Acceso con resumen criptográfico | generate_password_hash y check_password_hash |
| JSON propio | GET /api/calculos (requiere sesión) |
| Servicio externo con requests | Open Food Facts, tiempo máximo y manejo de errores |
| Streamlit y Pandas | tablero.py |
| Dirección pública | Completar siguiendo PUBLICACION.md |

## Entrega

El archivo `NutriDiario-entrega.zip` contiene solo fuentes y documentación.
Antes de entregar: completar la publicación y anotar las direcciones reales en el
informe. Clara Gariglio está a cargo del contenido, Ramiro Arias del diseño y ambos
de las pruebas. No agregar
credenciales a los archivos ni al comprimido.

Para repetir las pruebas locales: `.\.venv\Scripts\python.exe comprobar.py`.
Las pruebas usan una base temporal, sin modificar los usuarios de la aplicación.
