// Punto de entrada del panel: el marco de marca y las rutas por hash.
import './shared/marca/tokens.css';
import './shared/ui/estilos.css';
import './app/app.css';
import { inicio } from './app/inicio';
import { arrancar, type Montador } from './app/rutas';
import { el, vacio } from './shared/ui/componentes';

// ponytail: Lanzar, Progreso y Lectura llegan en T-09, T-10 y T-13; hasta entonces, un aviso.
const pendiente = (titulo: string) => ({
  titulo,
  nodo: el('section', 'q-tarjeta', vacio('esta vista todavía no está disponible')),
  recursos: [],
});

const montar: Montador = (ruta) => {
  switch (ruta.vista) {
    case 'inicio':
      return inicio();
    case 'lanzar':
      return pendiente('Lanzar');
    case 'progreso':
      return pendiente('Progreso');
    case 'lectura':
      return pendiente('Lectura');
  }
};

const app = document.querySelector<HTMLElement>('#app');
if (app) arrancar(app, montar);
