// Los formularios se procesan en Flask; esta validación ayuda antes de enviarlos.
document.querySelectorAll('.formulario').forEach(formulario => {
  formulario.addEventListener('submit', evento => {
    const mensaje = formulario.querySelector('.error-cliente');
    mensaje.textContent = '';
    const nombre = formulario.querySelector('[name="nombre"]');
    if (nombre && nombre.value.trim().length < 2) {
      evento.preventDefault();
      mensaje.textContent = 'Ingresá un nombre de al menos 2 caracteres.';
      nombre.focus();
    }
  });
});

const botonJson = document.querySelector('#ver-json');
if (botonJson) {
  botonJson.addEventListener('click', async () => {
    const salida = document.querySelector('#datos-json');
    salida.hidden = false;
    salida.textContent = 'Cargando tus datos…';
    try {
      const respuesta = await fetch('/api/calculos');
      if (!respuesta.ok) throw new Error('No se pudieron obtener los datos. Volvé a ingresar.');
      salida.textContent = JSON.stringify(await respuesta.json(), null, 2);
    } catch (error) {
      salida.textContent = error.message;
    }
  });
}
