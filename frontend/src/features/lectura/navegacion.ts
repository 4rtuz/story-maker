// El teclado de Lectura (RF-28, D47): ← y → mueven la selección sin dar la vuelta en los extremos,
// Enter abre el seleccionado y Esc cierra el lector. Una tecla sin efecto devuelve null.

export interface Pulsacion {
  seleccion: number;
  accion?: 'abrir' | 'cerrar';
}

export function tecla(key: string, seleccion: number, total: number): Pulsacion | null {
  switch (key) {
    case 'ArrowLeft':
      return { seleccion: Math.max(1, seleccion - 1) };
    case 'ArrowRight':
      return { seleccion: Math.min(total, seleccion + 1) };
    case 'Enter':
      return { seleccion, accion: 'abrir' };
    case 'Escape':
      return { seleccion, accion: 'cerrar' };
    default:
      return null;
  }
}
