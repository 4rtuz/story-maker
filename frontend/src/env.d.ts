/// <reference types="vite/client" />

// La única variable del panel (spec 0004 §8.4): nada secreto pasa por VITE_*, que va al bundle.
interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
}
