// Control positivo: un import relativo que se queda dentro de src/ y texto escrito como texto.
import { urlBase } from '../shared/api/cliente';

export function pintar(elemento: HTMLElement): void {
  elemento.textContent = urlBase();
}
