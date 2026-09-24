import { describe, expect, it } from 'vitest';
import { urlBase } from './cliente';

describe('URL de la API (CA-01)', () => {
  it('sin VITE_API_URL, la de uvicorn por defecto', () => {
    expect(urlBase({})).toBe('http://127.0.0.1:8000');
    expect(urlBase()).toBe('http://127.0.0.1:8000');
  });

  it('con VITE_API_URL, esa', () => {
    expect(urlBase({ VITE_API_URL: 'http://127.0.0.1:9000' })).toBe('http://127.0.0.1:9000');
  });
});
