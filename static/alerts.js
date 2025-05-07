
function formatearValor(input) {
    // Eliminar todos los caracteres no numéricos
    let valor = input.value.replace(/\D/g, '');
    
    // Si no hay valor, dejar campos vacíos
    if (valor === '') {
        input.value = '';
        document.getElementById('valor').value = '';
        return;
    }
    
    // Convertir a número
    let numero = parseInt(valor, 10);
    
    // Guardar el valor numérico en el campo oculto
    document.getElementById('valor').value = numero;
    
    // Formatear con separador de miles para mostrar
    input.value = numero.toLocaleString('es-ES');
}