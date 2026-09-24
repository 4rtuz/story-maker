// Punto de entrada del panel. Las vistas llegan con app/ (T-07).
import './shared/marca/tokens.css';
import './shared/ui/estilos.css';

const app = document.querySelector<HTMLElement>('#app');
if (app) app.textContent = 'Panel de novelas';
