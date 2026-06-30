import os
import re
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tesis_datos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# CAMBIA ESTA CLAVE POR UNA SECRETA Y SEGURA
app.config['SECRET_KEY'] = 'una_clave_muy_secreta_para_sesiones'

db = SQLAlchemy(app)

# ================= MODELOS =================
class Avenida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), unique=True, nullable=False)
    puntos = db.relationship('Punto', backref='avenida', lazy=True, cascade="all, delete-orphan")

class Punto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    avenida_id = db.Column(db.Integer, db.ForeignKey('avenida.id'), nullable=False)
    pano_id = db.Column(db.String(100), nullable=False, unique=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.String(10), nullable=False)
    url_original = db.Column(db.String(500), nullable=True)
    sentido = db.Column(db.String(10), nullable=False)

# ================= FUNCIONES =================
def extraer_pano_id_de_url(url):
    match = re.search(r'!1s([a-zA-Z0-9_\-]+)', url)
    print(match.group(1) if match else url.strip())
    return match.group(1) if match else url.strip()


def asegurar_esquema_db():
    inspector = inspect(db.engine)
    if 'punto' not in inspector.get_table_names():
        return

    columnas = {col['name'] for col in inspector.get_columns('punto')}
    if 'sentido' not in columnas:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE punto ADD COLUMN sentido VARCHAR(10) NOT NULL DEFAULT 'Ida'"))


def consultar_google_metadata(pano_id):
    # ¡SEGURIDAD!: En producción, usa variables de entorno para esto
    API_KEY = os.getenv("API_KEY_GOOGLE")
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?pano={pano_id}&key={API_KEY}"
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# ================= RUTAS =================
@app.route('/')
def index():
    avenidas = Avenida.query.order_by(Avenida.id.asc()).all()
    avenida_seleccionada_id = session.get('config_avenida_id')

    if avenida_seleccionada_id:
        puntos = Punto.query.filter_by(avenida_id=avenida_seleccionada_id).order_by(Punto.id.desc()).all()
        puntos_actuales = Punto.query.filter_by(avenida_id=avenida_seleccionada_id).count()
    else:
        puntos = Punto.query.order_by(Punto.id.desc()).all()
        puntos_actuales = 0

    total_puntos = Punto.query.count()
    avenida_actual = Avenida.query.get(avenida_seleccionada_id) if avenida_seleccionada_id else None

    return render_template(
        'index.html',
        avenidas=avenidas,
        puntos=puntos,
        total_puntos=total_puntos,
        puntos_actuales=puntos_actuales,
        avenida_actual=avenida_actual,
    )

@app.route('/avenidas')
def avenidas_page():
    avenidas = Avenida.query.order_by(Avenida.id.asc()).all()
    return render_template('avenidas.html', avenidas=avenidas)

@app.route('/configurar', methods=['POST'])
def configurar():
    session['config_avenida_id'] = request.form.get('avenida_id')
    session['config_sentido'] = request.form.get('sentido')
    flash('Configuración guardada. Puedes empezar a extraer puntos.', 'success')
    return redirect(url_for('index'))

@app.route('/punto/nuevo', methods=['POST'])
def nuevo_punto():
    avenida_id = request.form.get('avenida_id') or session.get('config_avenida_id')
    sentido = request.form.get('sentido') or session.get('config_sentido') or 'Ida'
    url_input = request.form.get('url_google', '').strip()

    if not avenida_id:
        flash('Error: Primero debes seleccionar una avenida.', 'error')
        return redirect(url_for('index'))

    pano_id = extraer_pano_id_de_url(url_input)
    if not pano_id:
        flash('Debes ingresar una URL o un Pano ID válido.', 'error')
        return redirect(url_for('index'))

    if Punto.query.filter_by(pano_id=pano_id).first():
        flash('Este punto ya existe.', 'error')
        return redirect(url_for('index'))

    metadata = consultar_google_metadata(pano_id)
    if metadata and metadata.get('status') == 'OK':
        nuevo_pto = Punto(
            avenida_id=avenida_id,
            pano_id=pano_id,
            lat=metadata['location']['lat'],
            lon=metadata['location']['lng'],
            fecha=metadata.get('date', '0000-00'),
            url_original=url_input,
            sentido=sentido
        )
        db.session.add(nuevo_pto)
        db.session.commit()
        flash(f'Punto guardado en {sentido}.', 'success')
    else:
        flash('Error al obtener datos de Google.', 'error')
    return redirect(url_for('index'))

@app.route('/avenida/nueva', methods=['POST'])
def nueva_avenida():
    nombre = request.form.get('nombre', '').strip()
    if not nombre:
        flash('El nombre de la avenida no puede estar vacío.', 'error')
    else:
        existe = Avenida.query.filter_by(nombre=nombre).first()
        if existe:
            flash('Ya existe una avenida con ese nombre.', 'error')
        else:
            db.session.add(Avenida(nombre=nombre))
            db.session.commit()
            flash('Avenida creada correctamente.', 'success')
    return redirect(url_for('index'))

@app.route('/avenida/editar/<int:id>', methods=['POST'])
def editar_avenida(id):
    avenida = Avenida.query.get_or_404(id)
    nombre = request.form.get('nombre', '').strip()
    if not nombre:
        flash('El nombre de la avenida no puede estar vacío.', 'error')
    else:
        existe = Avenida.query.filter(Avenida.nombre == nombre, Avenida.id != id).first()
        if existe:
            flash('Ya existe una avenida con ese nombre.', 'error')
        else:
            avenida.nombre = nombre
            db.session.commit()
            flash('Avenida actualizada correctamente.', 'success')
    return redirect(url_for('index'))

@app.route('/avenida/eliminar/<int:id>', methods=['POST'])
def eliminar_avenida(id):
    avenida = Avenida.query.get_or_404(id)
    db.session.delete(avenida)
    db.session.commit()
    flash('Avenida eliminada correctamente.', 'success')
    return redirect(url_for('index'))

@app.route('/punto/editar/<int:id>', methods=['POST'])
def editar_punto(id):
    punto = Punto.query.get_or_404(id)
    avenida_id = request.form.get('avenida_id')
    url_input = request.form.get('url_google', '').strip()

    if not avenida_id:
        flash('Debes seleccionar una avenida.', 'error')
        return redirect(url_for('index'))

    pano_id = extraer_pano_id_de_url(url_input)
    if not pano_id:
        pano_id = punto.pano_id

    existente = Punto.query.filter(Punto.pano_id == pano_id, Punto.id != id).first()
    if existente:
        flash('Este punto ya está registrado en otro registro.', 'error')
        return redirect(url_for('index'))

    metadata = consultar_google_metadata(pano_id)
    if metadata and metadata.get('status') == 'OK':
        punto.avenida_id = int(avenida_id)
        punto.pano_id = pano_id
        punto.lat = metadata['location']['lat']
        punto.lon = metadata['location']['lng']
        punto.fecha = metadata.get('date', '0000-00')
        punto.url_original = url_input
        db.session.commit()
        flash('Punto actualizado correctamente.', 'success')
    else:
        flash('No se pudo actualizar el punto. Verifica el Pano ID o la URL.', 'error')

    return redirect(url_for('index'))

@app.route('/punto/eliminar/<int:id>', methods=['POST'])
def eliminar_punto(id):
    punto = Punto.query.get_or_404(id)
    db.session.delete(punto)
    db.session.commit()
    flash('Punto eliminado correctamente.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        asegurar_esquema_db()
    app.run(debug=True)