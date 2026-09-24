-- Generado por `novela verificar-lean demo-partida`. No editar: se regenera desde el estado.
import StoryMaker.Invariantes
open StoryMaker

-- personaje 0: per-elena-vidal
-- personaje 1: per-ines-mar
-- personaje 2: per-tomas-reyes
-- lugar 0: esc-casa-del-faro
-- lugar 1: esc-puerto

def cronologia : Cronologia where
  eventos := [
    -- 0: evt-01-1
    { id := 0, momento := 1260, duracion := 40, lugar := 0,
      presentes := [0, 2], excluidos := [],
      edades := [(0, 40)], tras := [] },
    -- 1: evt-02-1
    { id := 1, momento := 1860, duracion := 0, lugar := 1,
      presentes := [2], excluidos := [2],
      edades := [], tras := [0] },
    -- 2: evt-03-1
    { id := 2, momento := 4140, duracion := 0, lugar := 0,
      presentes := [0, 2], excluidos := [],
      edades := [], tras := [1] },
    -- 3: evt-03-2
    { id := 3, momento := 1270, duracion := 0, lugar := 1,
      presentes := [2, 1], excluidos := [],
      edades := [], tras := [] }
  ]
  edadAlInicio := [(0, 40), (1, 40), (2, 40)]

#eval informe cronologia

theorem orden : respetaOrden cronologia = true := by decide +kernel
example : RespetaOrden cronologia := respetaOrden_correcto _ orden
theorem edad : edadesCoherentes cronologia = true := by decide +kernel
example : EdadesCoherentes cronologia := edadesCoherentes_correcto _ edad
theorem ubicuidad : sinUbicuidad cronologia = true := by decide +kernel
example : SinUbicuidad cronologia := sinUbicuidad_correcto _ ubicuidad
theorem exclusion : respetaExclusiones cronologia = true := by decide +kernel
example : RespetaExclusiones cronologia := respetaExclusiones_correcto _ exclusion
