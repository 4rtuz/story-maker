---------------------------- MODULE Regeneraciones ----------------------------
(***************************************************************************)
(* Dos `novela cambio` a la vez sobre la misma novela terminada (rama      *)
(* spec-0007, slices/cambio/cmd.py y plataforma/versiones.py).             *)
(*                                                                         *)
(* Lo que modela del código: las comprobaciones de `_nueva_peticion` y el  *)
(* id y la versión base se leen FUERA del lock; `registrar_peticion`,      *)
(* `preparar` (copiar a versiones/vN/, vaciar, base nueva) van DENTRO de   *)
(* `ws.bloquear()`, que no espera: si está tomado sale con 3.  Entre medias*)
(* el bucle regenera la versión nueva, con el mismo lock.                  *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets

CONSTANTS Procs, Mutante   \* Mutante: "ninguno" | "sin_guarda" (sin RF-21)
ASSUME Mutante \in {"ninguno", "sin_guarda"}

Criticos == {"registrar", "copiar", "vaciar"}
Finales == {"hecho", "rechazado", "ocupado", "inexplicada"}

VARIABLES
    pc, base, id,      \* de cada proceso
    lock,              \* estado/state.lock: "libre" o el proceso que lo tiene
    version,           \* meta.version de la raíz
    completa,          \* la raíz tiene el checkpoint del último capítulo
    guardadas,         \* números de versiones/vN/ confirmados
    ultimo,            \* último cambios/cam-NNN.json
    trabajo            \* fantasma: versiones que llegaron a estar completas

vars == <<pc, base, id, lock, version, completa, guardadas, ultimo, trabajo>>

TypeOK ==
    /\ pc \in [Procs -> {"inicio", "lock"} \cup Criticos \cup Finales]
    /\ base \in [Procs -> Nat] /\ id \in [Procs -> Nat]
    /\ lock \in Procs \cup {"libre"}
    /\ version \in Nat /\ completa \in BOOLEAN /\ guardadas \subseteq Nat
    /\ ultimo \in [id: Nat, estado: {"ninguno", "preparando", "en_curso"}]

Init ==
    /\ pc = [p \in Procs |-> "inicio"] /\ base = [p \in Procs |-> 0]
    /\ id = [p \in Procs |-> 0] /\ lock = "libre"
    /\ version = 1 /\ completa = TRUE /\ guardadas = {}
    /\ ultimo = [id |-> 0, estado |-> "ninguno"] /\ trabajo = {1}

\* _nueva_peticion, sin lock: terminada, sin cambio en curso ni en preparación
Comprobar(p) ==
    /\ pc[p] = "inicio"
    /\ IF completa /\ ultimo.estado # "preparando"
       THEN /\ pc' = [pc EXCEPT ![p] = "lock"]
            /\ base' = [base EXCEPT ![p] = version]
            /\ id' = [id EXCEPT ![p] = ultimo.id + 1]
       ELSE pc' = [pc EXCEPT ![p] = "rechazado"] /\ UNCHANGED <<base, id>>
    /\ UNCHANGED <<lock, version, completa, guardadas, ultimo, trabajo>>

\* ws.bloquear(): FileLock con timeout=0
Tomar(p) ==
    /\ pc[p] = "lock"
    /\ IF lock = "libre"
       THEN lock' = p /\ pc' = [pc EXCEPT ![p] = "registrar"]
       ELSE pc' = [pc EXCEPT ![p] = "ocupado"] /\ UNCHANGED lock
    /\ UNCHANGED <<base, id, version, completa, guardadas, ultimo, trabajo>>

\* registrar_peticion: RF-21, vN/ existe sin un preparando que lo explique -> 4
Registrar(p) ==
    /\ pc[p] = "registrar"
    /\ LET explicado == ultimo.id = id[p] /\ ultimo.estado = "preparando"
       IN IF base[p] \in guardadas /\ ~explicado /\ Mutante # "sin_guarda"
          THEN /\ pc' = [pc EXCEPT ![p] = "inexplicada"] /\ lock' = "libre"
               /\ UNCHANGED ultimo
          ELSE /\ pc' = [pc EXCEPT ![p] = "copiar"]
               /\ ultimo' = [id |-> id[p], estado |-> "preparando"]
               /\ UNCHANGED lock
    /\ UNCHANGED <<base, id, version, completa, guardadas, trabajo>>

\* preparar: si vN/ no existe se copia y se renombra; si existe, se sigue
Copiar(p) ==
    /\ pc[p] = "copiar" /\ pc' = [pc EXCEPT ![p] = "vaciar"]
    /\ guardadas' = guardadas \cup {base[p]}
    /\ UNCHANGED <<base, id, lock, version, completa, ultimo, trabajo>>

\* _vaciar + _base_nueva + en_curso, y el lock se suelta
Vaciar(p) ==
    /\ pc[p] = "vaciar" /\ pc' = [pc EXCEPT ![p] = "hecho"]
    /\ version' = base[p] + 1 /\ completa' = FALSE
    /\ ultimo' = [ultimo EXCEPT !.estado = "en_curso"] /\ lock' = "libre"
    /\ UNCHANGED <<base, id, guardadas, trabajo>>

\* El bucle regenera la versión nueva hasta el último checkpoint (con lock)
Regenerar ==
    /\ lock = "libre" /\ ultimo.estado = "en_curso" /\ ~completa
    /\ completa' = TRUE /\ trabajo' = trabajo \cup {version}
    /\ UNCHANGED <<pc, base, id, lock, version, guardadas, ultimo>>

Fin == \A p \in Procs: pc[p] \in Finales /\ UNCHANGED vars

Proc(p) == Comprobar(p) \/ Tomar(p) \/ Registrar(p) \/ Copiar(p) \/ Vaciar(p)
Next == (\E p \in Procs: Proc(p)) \/ Regenerar \/ Fin
Spec == Init /\ [][Next]_vars /\ \A p \in Procs: WF_vars(Proc(p))

\* Nunca dos escritores a la vez: quien está en la sección crítica tiene el lock.
UnSoloEscritor == \A p \in Procs: pc[p] \in Criticos => lock = p

\* Ninguna versión se pierde: toda versión que llegó a estar completa sigue
\* completa en la raíz o está guardada en versiones/vN/.
NingunaPerdida == \A v \in trabajo: v \in guardadas \/ (v = version /\ completa)

\* Una versión nueva por cambio que termina.
UnaVersionPorCambio == Cardinality({p \in Procs: pc[p] = "hecho"}) = version - 1

Terminan == <>(\A p \in Procs: pc[p] \in Finales)
=============================================================================
