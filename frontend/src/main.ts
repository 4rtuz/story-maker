// Punto de entrada del panel: el marco de marca y las rutas por hash.
import './shared/marca/tokens.css';
import './shared/ui/estilos.css';
import './app/app.css';
import { inicio } from './app/inicio';
import { arrancar, type Montador } from './app/rutas';
import { lanzar } from './features/lanzar/vista';
import { progreso } from './features/progreso/vista';
import { el, vacio } from './shared/ui/componentes';

// ponytail: Lectura llega en T-13; hasta entonces, un aviso.
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
      return lanzar();
    case 'progreso':
      return progreso(ruta);
    case 'lectura':
      return pendiente('Lectura');
  }
};

const app = document.querySelector<HTMLElement>('#app');
if (app) arrancar(app, montar);
