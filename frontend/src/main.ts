// Punto de entrada del panel: el marco de marca y las rutas por hash.
import './shared/marca/tokens.css';
import './shared/ui/estilos.css';
import './app/app.css';
import { inicio } from './app/inicio';
import { arrancar, type Montador } from './app/rutas';
import { lanzar } from './features/lanzar/vista';
import { lectura } from './features/lectura/vista';
import { progreso } from './features/progreso/vista';

const montar: Montador = (ruta, navegar) => {
  switch (ruta.vista) {
    case 'inicio':
      return inicio();
    case 'lanzar':
      return lanzar();
    case 'progreso':
      return progreso(ruta);
    case 'lectura':
      return lectura(ruta, navegar);
  }
};

const app = document.querySelector<HTMLElement>('#app');
if (app) arrancar(app, montar);
