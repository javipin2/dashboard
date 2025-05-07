# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Reemplaza por una clave segura en producción

# Configuración de la base de datos
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',      # Ingresa tu contraseña si es necesaria
    'database': 'cancha_dueño',
    'port': 3306
}

def get_db_connection():
    """Retorna una conexión a la base de datos."""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as err:
        print(f"Error de conexión: {err}")
        return None

# Decorador para rutas protegidas
def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return decorated_function

# ---------------------------
# AUTENTICACIÓN
# ---------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login de administrador (usuario: admin / contraseña: admin123).
    """
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        if usuario == 'admin' and contrasena == 'admin123':
            session['logged_in'] = True
            session['admin_user'] = usuario
            flash('Bienvenido, administrador', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales inválidas', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

# ---------------------------
# DASHBOARD Y MENÚ PRINCIPAL
# ---------------------------
@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# ---------------------------
# GESTIÓN DE CLIENTES
# ---------------------------
@app.route('/clientes')
@login_required
def clientes():
    """Lista los clientes registrados."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM clientes ORDER BY id DESC"
        cursor.execute(query)
        clientes_list = cursor.fetchall()
    except Error as err:
        flash(f'Error al cargar clientes: {err}', 'danger')
        clientes_list = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template('clientes.html', clientes=clientes_list)

@app.route('/registrar_cliente', methods=['GET', 'POST'])
@login_required
def registrar_cliente():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        correo = request.form.get('correo')
        if not nombre or not telefono:
            flash('El nombre y teléfono son requeridos.', 'warning')
            return redirect(url_for('registrar_cliente'))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "INSERT INTO clientes (nombre, telefono, correo) VALUES (%s, %s, %s)"
            cursor.execute(query, (nombre, telefono, correo))
            conn.commit()
            flash('Cliente registrado con éxito', 'success')
            return redirect(url_for('clientes'))
        except Error as err:
            flash(f'Error al registrar cliente: {err}', 'danger')
            return redirect(url_for('registrar_cliente'))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    return render_template('registrar_cliente.html')

@app.route('/edit_cliente/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def edit_cliente(cliente_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        correo = request.form.get('correo')
        try:
            query = "UPDATE clientes SET nombre = %s, telefono = %s, correo = %s WHERE id = %s"
            cursor.execute(query, (nombre, telefono, correo, cliente_id))
            conn.commit()
            flash('Cliente actualizado correctamente', 'success')
            return redirect(url_for('clientes'))
        except Error as err:
            flash(f'Error al actualizar cliente: {err}', 'danger')
            return redirect(url_for('edit_cliente', cliente_id=cliente_id))
        finally:
            cursor.close()
            conn.close()
    else:
        query = "SELECT * FROM clientes WHERE id = %s"
        cursor.execute(query, (cliente_id,))
        cliente = cursor.fetchone()
        cursor.close()
        conn.close()
        if not cliente:
            flash('Cliente no encontrado', 'warning')
            return redirect(url_for('clientes'))
        return render_template('editar_clientes.html', cliente=cliente)

@app.route('/delete_cliente/<int:cliente_id>', methods=['POST'])
@login_required
def delete_cliente(cliente_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "DELETE FROM clientes WHERE id = %s"
        cursor.execute(query, (cliente_id,))
        conn.commit()
        flash('Cliente eliminado', 'success')
    except Error as err:
        flash(f'Error al eliminar cliente: {err}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for('clientes'))

# ---------------------------
# GESTIÓN DE "SEDES" (OBTENIDAS DESDE EL CAMPO sede DE canchas)
# ---------------------------
@app.route('/sedes')
@login_required
def sedes():
    """
    Lista los valores distintos de la columna 'sede' de la tabla canchas.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT DISTINCT sede FROM canchas ORDER BY sede"
        cursor.execute(query)
        sedes_list = cursor.fetchall()  # Cada registro tiene {"sede": "Sede 1"}, etc.
    except Error as err:
        flash(f'Error al cargar sedes: {err}', 'danger')
        sedes_list = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template('sedes.html', sedes=sedes_list)

@app.route('/edit_sede_value/<string:old_value>', methods=['GET', 'POST'])
@login_required
def edit_sede_value(old_value):
    """
    Permite actualizar el valor de una sede para todas las canchas que tengan el valor antiguo.
    """
    if request.method == 'POST':
        new_value = request.form.get('new_value')
        if not new_value:
            flash('El nuevo valor es requerido.', 'warning')
            return redirect(url_for('edit_sede_value', old_value=old_value))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "UPDATE canchas SET sede = %s WHERE sede = %s"
            cursor.execute(query, (new_value, old_value))
            conn.commit()
            flash('Sede actualizada exitosamente', 'success')
            return redirect(url_for('sedes'))
        except Error as err:
            flash(f'Error al actualizar la sede: {err}', 'danger')
            return redirect(url_for('edit_sede_value', old_value=old_value))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    return render_template('editar_sede.html', old_value=old_value)

# ---------------------------
# GESTIÓN DE CANCHAS
# ---------------------------
@app.route('/canchas_admin')
@login_required
def canchas_admin():
    """
    Lista todas las canchas.
    Se puede filtrar por sede (usando el parámetro GET "sede").
    Además, se envía la lista de sedes (distintas) para el dropdown de filtrado.
    """
    sede_filter = request.args.get('sede')
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if sede_filter:
            query = """
              SELECT * FROM canchas
              WHERE sede = %s
              ORDER BY id DESC
            """
            cursor.execute(query, (sede_filter,))
        else:
            query = "SELECT * FROM canchas ORDER BY id DESC"
            cursor.execute(query)
        canchas_list = cursor.fetchall()
    except Error as err:
        flash(f'Error al cargar canchas: {err}', 'danger')
        canchas_list = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    # Para el filtro, obtener los valores distintos de sede
    sedes_list = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DISTINCT sede FROM canchas ORDER BY sede")
        sedes_list = cursor.fetchall()
    except Error as err:
        flash(f'Error al cargar sedes para filtro: {err}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template('canchas_admin.html', canchas=canchas_list, sedes=sedes_list, sede_filter=sede_filter)

@app.route('/registrar_cancha', methods=['GET', 'POST'])
@login_required
def registrar_cancha():
    # Para el select de sede, obtener los valores distintos; o, alternativamente, se puede permitir escribir el valor.
    sedes_list = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DISTINCT sede FROM canchas ORDER BY sede")
        sedes_list = cursor.fetchall()
    except Error as err:
        flash(f'Error al cargar sedes: {err}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        imagen = request.form.get('imagen')  # Mejor usar carga de archivos en producción
        techada = 1 if request.form.get('techada') == 'on' else 0
        ubicacion = request.form.get('ubicacion')
        precio = request.form.get('precio')
        servicios = request.form.get('servicios')
        sede = request.form.get('sede')  # Se espera que se ingrese o seleccione el valor deseado
        if not nombre or not sede:
            flash('El nombre y la sede son requeridos', 'warning')
            return redirect(url_for('registrar_cancha'))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO canchas (nombre, descripcion, imagen, techada, ubicacion, precio, servicios, sede)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nombre, descripcion, imagen, techada, ubicacion, precio, servicios, sede))
            conn.commit()
            flash('Cancha registrada exitosamente', 'success')
            return redirect(url_for('canchas_admin'))
        except Error as err:
            flash(f'Error al registrar cancha: {err}', 'danger')
            return redirect(url_for('registrar_cancha'))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    return render_template('registrar_cancha.html', sedes=sedes_list)

@app.route('/edit_cancha/<int:cancha_id>', methods=['GET', 'POST'])
@login_required
def edit_cancha(cancha_id):
    sedes_list = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DISTINCT sede FROM canchas ORDER BY sede")
        sedes_list = cursor.fetchall()
    except Error as err:
        flash(f'Error al cargar sedes: {err}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        imagen = request.form.get('imagen')
        techada = 1 if request.form.get('techada') == 'on' else 0
        ubicacion = request.form.get('ubicacion')
        precio = request.form.get('precio')
        servicios = request.form.get('servicios')
        sede = request.form.get('sede')
        try:
            query = """
                UPDATE canchas SET nombre=%s, descripcion=%s, imagen=%s, techada=%s,
                ubicacion=%s, precio=%s, servicios=%s, sede=%s WHERE id=%s
            """
            cursor.execute(query, (nombre, descripcion, imagen, techada, ubicacion, precio, servicios, sede, cancha_id))
            conn.commit()
            flash('Cancha actualizada correctamente', 'success')
            return redirect(url_for('canchas_admin'))
        except Error as err:
            flash(f'Error al actualizar cancha: {err}', 'danger')
            return redirect(url_for('edit_cancha', cancha_id=cancha_id))
        finally:
            cursor.close()
            conn.close()
    else:
        query = "SELECT * FROM canchas WHERE id = %s"
        cursor.execute(query, (cancha_id,))
        cancha = cursor.fetchone()
        cursor.close()
        conn.close()
        if not cancha:
            flash('Cancha no encontrada', 'warning')
            return redirect(url_for('canchas_admin'))
        return render_template('editar_cancha.html', cancha=cancha, sedes=sedes_list)

@app.route('/delete_cancha/<int:cancha_id>', methods=['POST'])
@login_required
def delete_cancha(cancha_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "DELETE FROM canchas WHERE id = %s"
        cursor.execute(query, (cancha_id,))
        conn.commit()
        flash('Cancha eliminada', 'success')
    except Error as err:
        flash(f'Error al eliminar cancha: {err}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for('canchas_admin'))

# ---------------------------
# GRAFICAS E INFORMES
# ---------------------------
@app.route('/graficas')
@login_required
def graficas():
    """Vista principal de gráficas."""
    return render_template('graficas.html')

@app.route('/graficas/general')
@login_required
def graficas_general():
    """Informe general: reservas por hora (8:00 a 23:00)."""
    horas = [f"{h}:00" for h in range(8, 24)]
    reservas_por_hora = [0] * len(horas)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT HOUR(hora) AS hr, COUNT(*) AS cnt FROM reservas GROUP BY HOUR(hora)"
        cursor.execute(query)
        data = cursor.fetchall()
        for row in data:
            hr, cnt = row
            if hr >= 8 and hr < 24:
                reservas_por_hora[hr - 8] = cnt
    except Error as err:
        flash(f'Error al cargar datos generales: {err}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template('graficas_general.html', horas=horas, reservas=reservas_por_hora)

@app.route('/graficas/diario')
@login_required
def graficas_diario():
    today = datetime.now().date()
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM reservas WHERE fecha = %s"
        cursor.execute(query, (today,))
        reservas = cursor.fetchall()
    except Error as err:
        flash(f'Error al cargar informe diario: {err}', 'danger')
        reservas = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template('graficas_diario.html', reservas=reservas, fecha=today)


@app.route('/reservas_fecha', methods=['GET'])
@login_required
def reservas_fecha():
    # Obtenemos la fecha enviada como parámetro (en formato 'YYYY-MM-DD')
    fecha = request.args.get('fecha')
    reservas_fecha = []
    if fecha:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # Consulta: seleccionamos todas las reservas cuya fecha sea la indicada
            query = "SELECT * FROM reservas WHERE fecha = %s ORDER BY hora ASC"
            cursor.execute(query, (fecha,))
            reservas_fecha = cursor.fetchall()
        except Error as err:
            flash(f'Error al cargar reservas: {err}', 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    # Renderizamos la plantilla especificando la fecha seleccionada y las reservas encontradas (si las hubiera)
    return render_template('reservas_fecha.html', reservas=reservas_fecha, fecha=fecha)


@app.route('/graficas/semanal')
@login_required
def graficas_semanal():
    today = datetime.now().date()
    semana_antes = today.fromordinal(today.toordinal()-6)
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM reservas WHERE fecha BETWEEN %s AND %s"
        cursor.execute(query, (semana_antes, today))
        reservas = cursor.fetchall()
    except Error as err:
        flash(f'Error al cargar informe semanal: {err}', 'danger')
        reservas = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template('graficas_semanal.html', reservas=reservas, inicio=semana_antes, fin=today)


# ---------------------------
# SECCIÓN RESERVAS
# ---------------------------

# Listar reservas por fecha (por defecto, día actual)
@app.route('/reservas', methods=['GET'])
@login_required
def reservas():
    fecha = request.args.get('fecha')
    if not fecha:
        fecha = datetime.now().strftime('%Y-%m-%d')  # Usar fecha actual si no se selecciona una
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM reservas WHERE fecha = %s ORDER BY hora ASC"
        cursor.execute(query, (fecha,))
        reservas_list = cursor.fetchall()
    except Error as err:
        flash(f"Error al cargar reservas: {err}", "danger")
        reservas_list = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('reservas.html', reservas=reservas_list, fecha=fecha)


@app.route('/get_ocupadas', methods=['GET'])
@login_required
def get_ocupadas():
    """Retorna las horas ocupadas en una fecha específica sin afectar otros campos."""
    fecha = request.args.get('fecha')
    occupied_hours = []

    if fecha:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "SELECT HOUR(hora) as hr FROM reservas WHERE fecha = %s"
            cursor.execute(query, (fecha,))
            results = cursor.fetchall()
            occupied_hours = [row[0] for row in results]
        except Error as err:
            return jsonify({"error": str(err)})
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return jsonify({"ocupadas": occupied_hours})


@app.route('/get_clientes', methods=['GET'])
@login_required
def get_clientes():
    """Retorna la lista de clientes registrados sin afectar el formulario."""
    clientes = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, telefono FROM clientes ORDER BY nombre")
        clientes = cursor.fetchall()
    except Error as err:
        return jsonify({"error": str(err)})
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return jsonify({"clientes": clientes})



# Agregar nueva reserva
@app.route('/agregar_reserva', methods=['GET', 'POST'])
@login_required
def agregar_reserva():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        cliente_id = request.form.get('cliente_id')  # ID del cliente seleccionado
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        estado = request.form.get('estado', 'Pendiente')
        valor = request.form.get('valor', 0)
        tipo_evento = request.form.get('tipo_evento', 'Fútbol')
        sede = request.form.get('sede', 'Sede 1')

        if not (nombre and telefono and fecha and hora):
            flash("Faltan datos requeridos.", "warning")
            return redirect(url_for('agregar_reserva', fecha=fecha))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Validar si la hora está ocupada
            query_check = "SELECT COUNT(*) FROM reservas WHERE fecha = %s AND hora = %s"
            cursor.execute(query_check, (fecha, hora))
            ocupado = cursor.fetchone()[0]
            if ocupado > 0:
                flash("Esta hora ya está ocupada, elige otra.", "warning")
                return redirect(url_for('agregar_reserva', fecha=fecha))

            # Insertar la reserva con nombre y teléfono del cliente seleccionado
            query_insert = """
                INSERT INTO reservas (nombre, telefono, fecha, hora, estado, valor, tipo_evento, sede)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_insert, (nombre, telefono, fecha, hora, estado, valor, tipo_evento, sede))
            conn.commit()
            flash("Reserva agregada exitosamente", "success")
            return redirect(url_for('reservas', fecha=fecha))
        except Error as err:
            flash(f"Error al agregar reserva: {err}", "danger")
            return redirect(url_for('agregar_reserva', fecha=fecha))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    else:
        fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))

        # Obtener lista de clientes registrados
        clientes = []
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, nombre, telefono FROM clientes ORDER BY nombre")
            clientes = cursor.fetchall()
        except Error as err:
            flash(f"Error al cargar clientes: {err}", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return render_template('agregar_reserva.html', fecha=fecha, clientes=clientes)
    




# Editar reserva
@app.route('/edit_reserva/<int:reserva_id>', methods=['GET', 'POST'])
@login_required
def edit_reserva(reserva_id):
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        estado = request.form.get('estado', 'Pendiente')
        valor = request.form.get('valor', 0)
        tipo_evento = request.form.get('tipo_evento', 'Fútbol')
        sede = request.form.get('sede', 'Sede 1')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
                UPDATE reservas 
                SET nombre=%s, telefono=%s, fecha=%s, hora=%s, estado=%s, valor=%s, tipo_evento=%s, sede=%s
                WHERE id = %s
            """
            cursor.execute(query, (nombre, telefono, fecha, hora, estado, valor, tipo_evento, sede, reserva_id))
            conn.commit()
            flash("Reserva actualizada correctamente", "success")
            return redirect(url_for('reservas', fecha=fecha))
        except Error as err:
            flash(f"Error al actualizar reserva: {err}", "danger")
            return redirect(url_for('edit_reserva', reserva_id=reserva_id))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    else:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM reservas WHERE id = %s"
            cursor.execute(query, (reserva_id,))
            reserva = cursor.fetchone()
        except Error as err:
            flash(f"Error al cargar reserva: {err}", "danger")
            return redirect(url_for('reservas'))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
        return render_template('editar_reserva.html', reserva=reserva)


# Eliminar reserva
@app.route('/delete_reserva/<int:reserva_id>', methods=['POST'])
@login_required
def delete_reserva(reserva_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "DELETE FROM reservas WHERE id = %s"
        cursor.execute(query, (reserva_id,))
        conn.commit()
        flash("Reserva eliminada correctamente", "success")
    except Error as err:
        flash(f"Error al eliminar reserva: {err}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for('reservas'))



@app.route('/graficas/mensual')
@login_required
def graficas_mensual():
    today = datetime.now().date()
    inicio_mes = today.replace(day=1)
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM reservas WHERE fecha BETWEEN %s AND %s"
        cursor.execute(query, (inicio_mes, today))
        reservas = cursor.fetchall()
    except Error as err:
        flash(f'Error al cargar informe mensual: {err}', 'danger')
        reservas = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template('graficas_mensual.html', reservas=reservas, inicio=inicio_mes, fin=today)

# ---------------------------
# NOTIFICACIONES
# ---------------------------
@app.route('/notificaciones')
@login_required
def notificaciones():
    # Notificaciones simuladas
    notificaciones_list = [
        {"mensaje": "Se realizó una reserva pendiente para la Cancha 1.", "fecha": datetime.now()},
        {"mensaje": "Se actualizó el estado de reserva a 'Pago Completo' en la Cancha 1.", "fecha": datetime.now()},
        {"mensaje": "Nuevo cliente registrado: 'Juan Pérez'.", "fecha": datetime.now()}
    ]
    return render_template('notificaciones.html', notificaciones=notificaciones_list)

# ---------------------------
# PERFIL DEL ADMINISTRADOR
# ---------------------------
@app.route('/perfil')
@login_required
def perfil():
    admin = {
        "nombre": "Administrador",
        "correo": "admin@canchalajugada.com",
        "foto": "/static/imagenes/admin.png"  # Asegúrate de tener esta imagen en static/imagenes
    }
    return render_template('perfil.html', admin=admin)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
