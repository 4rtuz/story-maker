------------------------------- MODULE Harness -------------------------------
(***************************************************************************)
(* El flujo de generación de una novela como máquina de estados:           *)
(* brief -> planificación -> capítulo a capítulo (escritura, validación,   *)
(* revisión, gates, registro, checkpoint) -> auditoría -> publicación, con  *)
(* reintentos acotados, caídas con reanudación desde checkpoints/latest.json*)
(* y regeneración por `novela cambio` (versión nueva, la anterior en        *)
(* versiones/).  La tabla acción -> fichero está en README.md.             *)
(*                                                                         *)
(* Lo que vive en disco (checkpoint, libro, log, versiones, export) sobre- *)
(* vive a una caída; lo que vive en la sesión (paso, fase) no.             *)
(***************************************************************************)
EXTENDS Naturals, Sequences

CONSTANTS
    N,            \* capítulos de la novela
    MaxReintentos,\* reintentos por gate: 2 en el procedimiento
    MaxCaidas,    \* cota de caídas de sesión, para que el modelo sea finito
    MaxCambios,   \* cota de `novela cambio`
    Mutante       \* "ninguno" o la guarda del código que se desactiva

Mutantes == {"ninguno", "sin_gate_revision", "reanudar_sin_checkpoint",
             "producir_por_export", "vaciar_sin_copia", "lectura_literal"}
ASSUME N \in Nat \ {0} /\ MaxReintentos \in Nat /\ MaxCaidas \in Nat
       /\ MaxCambios \in Nat /\ Mutante \in Mutantes

Fases == {"brief", "planificacion", "capitulo", "auditoria", "cambio",
          "caida", "publicada", "detenida", "intervencion"}
Terminales == {"publicada", "detenida", "intervencion"}
Pasos == {"escritor", "validar1", "revision", "validar2", "editor",
          "gate", "cronista", "aplicar", "checkpoint"}
Gates == {"brief", "arquitecto", "mecanico", "revision", "delta"}
DelCapitulo == {"mecanico", "revision", "delta"}  \* cuentan por run de capítulo

VARIABLES
    fase, cap, paso,          \* sesión: se pierden en una caída
    mec,        \* la última `validar` pasó sobre el texto actual (custodia)
    ver,        \* veredicto de continuidad+suspense sobre el texto actual
    delta,      \* estado/deltas/NN.json: "ninguno" | "escrito" | "aplicado"
    revDespues, \* hay un `briefing NN continuista` después de la última validar
    log,        \* harness.log: líneas que cuenta el procedimiento, por gate
    fallos,     \* fantasma: fallos reales por gate
    reintentos, \* fantasma: reintentos lanzados por gate
    checkpoint, \* checkpoints/latest.json: último capítulo cerrado
    libro,      \* capítulos cerrados, en orden, con si pasaron todo
    version,    \* meta.version de estado.db
    guardadas,  \* versiones/vN/: el libro de cada versión anterior
    cambioEstado, pasoCambio, \* cambios/cam-NNN.json y el punto de preparar
    auditada,   \* qa/auditoria.json aprobado en la versión vigente
    exportada,  \* versión de lo que hay en export/ (0: nada)
    caidas, cambios

vars == <<fase, cap, paso, mec, ver, delta, revDespues, log, fallos,
          reintentos, checkpoint, libro, version, guardadas, cambioEstado,
          pasoCambio, auditada, exportada, caidas, cambios>>
capVars == <<mec, ver, delta, revDespues>>

Ceros == [g \in Gates |-> 0]
SinCapitulo(f) == [g \in Gates |-> IF g \in DelCapitulo THEN 0 ELSE f[g]]

TypeOK ==
    /\ fase \in Fases /\ cap \in 1..N /\ paso \in Pasos
    /\ mec \in BOOLEAN /\ ver \in {"ninguno", "aprobado", "rechazado"}
    /\ delta \in {"ninguno", "escrito", "aplicado"} /\ revDespues \in BOOLEAN
    /\ log \in [Gates -> Nat] /\ fallos \in [Gates -> Nat]
    /\ reintentos \in [Gates -> Nat]
    /\ checkpoint \in 0..N /\ libro \in Seq([cap: 1..N, ok: BOOLEAN])
    /\ version \in 1..(MaxCambios + 1)
    /\ guardadas \in Seq(Seq([cap: 1..N, ok: BOOLEAN]))
    /\ cambioEstado \in {"ninguno", "preparando", "en_curso"}
    /\ pasoCambio \in {"registrado", "copiado"}
    /\ auditada \in BOOLEAN /\ exportada \in 0..(MaxCambios + 1)
    /\ caidas \in 0..MaxCaidas /\ cambios \in 0..MaxCambios

Init ==
    /\ fase = "brief" /\ cap = 1 /\ paso = "escritor"
    /\ mec = FALSE /\ ver = "ninguno" /\ delta = "ninguno" /\ revDespues = FALSE
    /\ log = Ceros /\ fallos = Ceros /\ reintentos = Ceros
    /\ checkpoint = 0 /\ libro = << >> /\ version = 1 /\ guardadas = << >>
    /\ cambioEstado = "ninguno" /\ pasoCambio = "registrado"
    /\ auditada = FALSE /\ exportada = 0 /\ caidas = 0 /\ cambios = 0

(***************************************************************************)
(* Cuenta de intentos (novela-continuar.md § Cuenta de intentos).  `log[g]`*)
(* ya incluye la línea del fallo actual en brief/arquitecto/mecánico/delta;*)
(* en revisión cuenta briefings de continuista, y los consumidos son todas  *)
(* menos una.  La lectura "intención" es la de spec 0003 (el tercer fallo   *)
(* para); "lectura_literal" aplica «con dos consumidos no reintenta» a la  *)
(* tabla de novela-continuar.md tal cual: hallazgo H-2.                    *)
(***************************************************************************)
\* Un gate falla: se apunta, y o se reintenta en `destino` o se interviene.
Falla(g, conLinea, destino) ==
    LET lineas    == IF conLinea THEN log[g] + 1 ELSE log[g]
        consumidos == IF g = "revision" THEN lineas - 1 ELSE lineas
        agotado   == IF g = "revision"
                        \/ (Mutante = "lectura_literal" /\ g \in DelCapitulo)
                     THEN consumidos >= MaxReintentos
                     ELSE consumidos > MaxReintentos
    IN /\ log' = [log EXCEPT ![g] = lineas]
       /\ fallos' = [fallos EXCEPT ![g] = @ + 1]
       /\ IF agotado
          THEN fase' = "intervencion" /\ UNCHANGED <<paso, reintentos>>
          ELSE /\ paso' = destino
               /\ reintentos' = [reintentos EXCEPT ![g] = @ + 1]
               /\ UNCHANGED fase

Resto == UNCHANGED
    (<<checkpoint, libro, version, guardadas, cambioEstado, pasoCambio,
       auditada, exportada, caidas, cambios, cap>>)

-----------------------------------------------------------------------------
(* Configuración y planificación.                                           *)

\* novela brief validar -> brief/brief.json (novela-brief.md)
BriefOK == fase = "brief" /\ fase' = "planificacion"
           /\ UNCHANGED <<cap, paso, capVars, log, fallos, reintentos>> /\ Resto
BriefFalla == fase = "brief" /\ Falla("brief", TRUE, paso)
              /\ UNCHANGED <<cap, capVars>> /\ Resto

\* /novela-nueva: arquitecto, `novela briefing 1 trazador` (su gate), trazador
PlanOK == fase = "planificacion" /\ fase' = "capitulo" /\ paso' = "escritor"
          /\ UNCHANGED <<cap, capVars, log, fallos, reintentos>> /\ Resto
PlanFalla == fase = "planificacion" /\ Falla("arquitecto", TRUE, paso)
             /\ UNCHANGED <<cap, capVars>> /\ Resto

-----------------------------------------------------------------------------
(* Bucle por capítulo (novela-continuar.md § Por capítulo).                 *)

EnPaso(p) == fase = "capitulo" /\ paso = p

\* Paso 2: briefing escritor + Task escritor -> capitulos/NN.md
Escribir == EnPaso("escritor") /\ paso' = "validar1"
            /\ mec' = FALSE /\ ver' = "ninguno"
            /\ UNCHANGED <<fase, delta, revDespues, log, fallos, reintentos>> /\ Resto

\* Pasos 3 y 5: novela validar (gate mecánico, en código)
ValidarOK(p, sig) == EnPaso(p) /\ paso' = sig /\ mec' = TRUE /\ revDespues' = FALSE
                     /\ UNCHANGED <<fase, ver, delta, log, fallos, reintentos>> /\ Resto
ValidarFalla(p, reintento) ==
    EnPaso(p) /\ mec' = FALSE /\ revDespues' = FALSE
    /\ Falla("mecanico", TRUE, reintento)
    /\ UNCHANGED <<ver, delta>> /\ Resto

\* Paso 4: tres briefings de revisión y tres Task; el editor reescribe
Revisar == EnPaso("revision") /\ paso' = "validar2"
           /\ ver' \in {"aprobado", "rechazado"} /\ mec' = FALSE /\ revDespues' = TRUE
           /\ log' = [log EXCEPT !["revision"] = @ + 1]
           /\ UNCHANGED <<fase, delta, fallos, reintentos>> /\ Resto

\* Paso 5, reintento: el editor-estilo con su mismo briefing
Editar == EnPaso("editor") /\ paso' = "validar2" /\ mec' = FALSE
          /\ UNCHANGED <<fase, ver, delta, revDespues, log, fallos, reintentos>> /\ Resto

\* Paso 6: gate de revisión.  Solo lo aplica el procedimiento (hallazgo H-1).
GateOK == EnPaso("gate") /\ (ver = "aprobado" \/ Mutante = "sin_gate_revision")
          /\ paso' = "cronista"
          /\ UNCHANGED <<fase, capVars, log, fallos, reintentos>> /\ Resto
GateFalla == EnPaso("gate") /\ ver = "rechazado" /\ Mutante # "sin_gate_revision"
             /\ Falla("revision", FALSE, "escritor")
             /\ UNCHANGED capVars /\ Resto

\* Paso 7: briefing cronista + Task cronista -> estado/deltas/NN.json
Cronista == EnPaso("cronista") /\ paso' = "aplicar" /\ delta' = "escrito"
            /\ UNCHANGED <<fase, mec, ver, revDespues, log, fallos, reintentos>> /\ Resto

\* Paso 7: novela aplicar-delta.  La custodia (en código) exige que la última
\* validar sea la del texto actual; si no, intervención sin reintento.
AplicarOK == EnPaso("aplicar") /\ mec /\ delta' = "aplicado" /\ paso' = "checkpoint"
             /\ UNCHANGED <<fase, mec, ver, revDespues, log, fallos, reintentos>> /\ Resto
AplicarFalla == EnPaso("aplicar") /\ mec /\ delta' = "escrito"
                /\ Falla("delta", TRUE, "cronista")
                /\ UNCHANGED <<mec, ver, revDespues>> /\ Resto
Custodia == EnPaso("aplicar") /\ ~mec /\ fase' = "intervencion"
            /\ UNCHANGED <<paso, capVars, log, fallos, reintentos>> /\ Resto

\* Paso 8: novela checkpoint.  Guarda en código: cursor en aplicar-delta.
\* Escribe NN.json y latest.json; es idempotente, así que se modela atómico.
Checkpoint ==
    /\ EnPaso("checkpoint") /\ delta = "aplicado"
    /\ libro' = Append(libro, [cap |-> cap, ok |-> mec /\ ver = "aprobado"])
    /\ checkpoint' = cap
    /\ IF cap = N
       THEN fase' = "auditoria" /\ UNCHANGED <<cap, paso, log, reintentos>>
       ELSE /\ cap' = cap + 1 /\ paso' = "escritor" /\ UNCHANGED fase
            /\ log' = SinCapitulo(log) /\ reintentos' = SinCapitulo(reintentos)
    /\ mec' = FALSE /\ ver' = "ninguno" /\ delta' = "ninguno" /\ revDespues' = FALSE
    /\ fallos' = IF cap = N THEN fallos ELSE SinCapitulo(fallos)
    /\ UNCHANGED <<version, guardadas, cambioEstado, pasoCambio, auditada,
                   exportada, caidas, cambios>>

-----------------------------------------------------------------------------
(* Auditoría y publicación (/novela-auditar, producir.flujo).               *)

\* novela auditar -> 0, y exportar md y epub
AuditarOK == fase = "auditoria" /\ fase' = "publicada"
             /\ auditada' = TRUE /\ exportada' = version
             /\ UNCHANGED <<cap, paso, capVars, log, fallos, reintentos, checkpoint,
                            libro, version, guardadas, cambioEstado, pasoCambio,
                            caidas, cambios>>
\* novela auditar -> 1: no exporta.  producir mira export/ (hallazgo H-3).
AuditarFalla ==
    /\ fase = "auditoria" /\ auditada' = FALSE
    /\ fase' = IF Mutante = "producir_por_export" /\ exportada # 0
               THEN "publicada" ELSE "detenida"
    /\ UNCHANGED <<cap, paso, capVars, log, fallos, reintentos, checkpoint, libro,
                   version, guardadas, cambioEstado, pasoCambio, exportada, caidas,
                   cambios>>

-----------------------------------------------------------------------------
(* Regeneración: novela cambio (rama spec-0007, versiones.py).              *)

\* _nueva_peticion: novela terminada, sin cambio en curso ni intervención viva
CambioRegistrar ==
    /\ fase \in {"publicada", "detenida"} /\ checkpoint = N /\ cambios < MaxCambios
    /\ cambioEstado # "preparando"
    /\ fase' = "cambio" /\ cambioEstado' = "preparando" /\ pasoCambio' = "registrado"
    /\ UNCHANGED <<cap, paso, capVars, log, fallos, reintentos, checkpoint, libro,
                   version, guardadas, auditada, exportada, caidas, cambios>>

\* _copiar + os.replace(vN.tmp, vN): el punto de confirmación
CambioCopiar ==
    /\ fase = "cambio" /\ pasoCambio = "registrado"
    /\ guardadas' = Append(guardadas, libro) /\ pasoCambio' = "copiado"
    /\ UNCHANGED <<fase, cap, paso, capVars, log, fallos, reintentos, checkpoint,
                   libro, version, cambioEstado, auditada, exportada, caidas, cambios>>

\* _vaciar + _base_nueva: raíz como la deja novela nueva, versión + 1.
\* export/ no está en COPIADOS: sobrevive.
CambioVaciar ==
    /\ fase = "cambio"
    /\ pasoCambio = "copiado" \/ Mutante = "vaciar_sin_copia"
    /\ fase' = "capitulo" /\ cap' = 1 /\ paso' = "escritor"
    /\ mec' = FALSE /\ ver' = "ninguno" /\ delta' = "ninguno" /\ revDespues' = FALSE
    /\ log' = SinCapitulo(log) /\ fallos' = SinCapitulo(fallos)
    /\ reintentos' = SinCapitulo(reintentos)
    /\ checkpoint' = 0 /\ libro' = << >> /\ version' = version + 1
    /\ cambioEstado' = "en_curso" /\ auditada' = FALSE /\ cambios' = cambios + 1
    /\ UNCHANGED <<guardadas, pasoCambio, exportada, caidas>>

-----------------------------------------------------------------------------
(* Caída y reanudación.                                                     *)

\* La sesión muere: se pierde lo que vivía en ella.  /novela-nueva no se
\* reanuda (flujo.py: «el workspace existe sin plan/escaleta.md»).
Caida ==
    /\ fase \in {"planificacion", "capitulo", "auditoria", "cambio"}
    /\ caidas < MaxCaidas /\ caidas' = caidas + 1
    /\ fase' = IF fase = "planificacion" THEN "detenida" ELSE "caida"
    /\ UNCHANGED <<cap, paso, capVars, log, fallos, reintentos, checkpoint, libro,
                   version, guardadas, cambioEstado, pasoCambio, auditada,
                   exportada, cambios>>

\* Punto de reanudación de novela-continuar.md, leído del disco
PasoDeReanudacion ==
    CASE delta = "aplicado"      -> "checkpoint"
      [] delta = "escrito"       -> "aplicar"
      [] mec /\ ~revDespues      -> "revision"
      [] OTHER                   -> "escritor"

\* Relanzar: cambio en preparando -> repetir la misma petición (RF-20);
\* si no, `novela pendiente` y cap = latest.json + 1.
Reanudar ==
    /\ fase = "caida"
    /\ IF cambioEstado = "preparando"
       THEN fase' = "cambio" /\ UNCHANGED <<cap, paso>>
       ELSE IF checkpoint = N
            THEN fase' = "auditoria" /\ UNCHANGED <<cap, paso>>
            ELSE /\ fase' = "capitulo"
                 /\ IF Mutante = "reanudar_sin_checkpoint"
                    THEN cap' = 1 /\ paso' = "escritor"
                    ELSE cap' = checkpoint + 1 /\ paso' = PasoDeReanudacion
    /\ UNCHANGED <<capVars, log, fallos, reintentos, checkpoint, libro, version,
                   guardadas, cambioEstado, pasoCambio, auditada, exportada,
                   caidas, cambios>>

\* Estado terminal: nada más que hacer (evita el falso deadlock).
Fin == fase \in Terminales /\ UNCHANGED vars

Progreso ==
    \/ BriefOK \/ BriefFalla \/ PlanOK \/ PlanFalla
    \/ Escribir \/ ValidarOK("validar1", "revision") \/ ValidarOK("validar2", "gate")
    \/ ValidarFalla("validar1", "escritor") \/ ValidarFalla("validar2", "editor")
    \/ Revisar \/ Editar \/ GateOK \/ GateFalla
    \/ Cronista \/ AplicarOK \/ AplicarFalla \/ Custodia \/ Checkpoint
    \/ AuditarOK \/ AuditarFalla
    \/ CambioCopiar \/ CambioVaciar \/ Reanudar

\* Caída y cambio son del entorno: sin equidad, acotados por constantes.
Next == Progreso \/ Caida \/ CambioRegistrar \/ Fin

Spec == Init /\ [][Next]_vars /\ WF_vars(Progreso)

-----------------------------------------------------------------------------
(* Invariantes.                                                             *)

Completo(l) == Len(l) = N /\ \A i \in 1..Len(l): l[i].cap = i /\ l[i].ok

\* 1. Ningún capítulo cerrado sin validar y revisión aprobados sobre su texto,
\*    y nunca se publica una versión incompleta, sin auditar o con otro export.
NuncaSinValidar == \A i \in 1..Len(libro): libro[i].ok
PublicadaValida ==
    fase = "publicada" => Completo(libro) /\ auditada /\ exportada = version

\* 2. La reanudación ni duplica ni pierde: el libro es 1..checkpoint, en orden.
ReanudacionExacta ==
    Len(libro) = checkpoint /\ \A i \in 1..Len(libro): libro[i].cap = i

\* 3. Cada versión anterior está guardada entera en versiones/vN/.
VersionAnteriorConservada ==
    /\ \A v \in 1..(version - 1): v <= Len(guardadas) /\ Completo(guardadas[v])
    /\ Len(guardadas) \in {version - 1, version}

\* 4. Los reintentos nunca superan el límite.
ReintentosAcotados == \A g \in Gates: reintentos[g] <= MaxReintentos

\* Lo que el procedimiento promete además: solo se interviene tras agotar un
\* gate con fallos reales.  No se cumple (H-2): ver HarnessCuenta.cfg.
IntervencionTrasAgotar ==
    fase = "intervencion" =>
        \/ \E g \in Gates: fallos[g] = MaxReintentos + 1
        \/ (paso = "aplicar" /\ ~mec)   \* custodia: sin reintento, a propósito

\* Temporal: versiones/ es append-only.
GuardadasSoloCrecen ==
    [][SubSeq(guardadas', 1, Len(guardadas)) = guardadas]_vars

\* Liveness: toda generación acaba publicada o parada con error, y ahí se queda.
Termina == <>[](fase \in Terminales)
=============================================================================
