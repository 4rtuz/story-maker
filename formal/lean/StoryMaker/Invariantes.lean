/-!
# Invariantes de la cronología de una novela

`novela verificar-lean` genera `formal/Cronologia.lean` desde la base de estado: una `Cronologia`
con ids numéricos (el generador deja la tabla id → nombre en comentarios) y un
`theorem … := by decide` por invariante. Si alguno no se cumple, la compilación falla.

Cada invariante es un checker `Bool` decidible más la proposición que expresa, con la prueba de
que el checker la implica para cualquier cronología.
-/

namespace StoryMaker

/-- Minutos de un año de 365 días. `momento` cuenta minutos desde el día 1 a las 00:00. -/
def minutosAño : Nat := 525600

structure Evento where
  id : Nat
  momento : Nat
  duracion : Nat := 0
  lugar : Nat
  presentes : List Nat := []
  /-- Personajes que el evento saca de la historia: muerte o partida definitiva. -/
  excluidos : List Nat := []
  /-- Edades que el texto declara en este evento: (personaje, años). -/
  edades : List (Nat × Nat) := []
  /-- Eventos que el texto declara anteriores a este. -/
  tras : List Nat := []
deriving Repr

structure Cronologia where
  eventos : List Evento
  /-- Edad de cada personaje en el momento 0, del canon: nació `edad` años antes. -/
  edadAlInicio : List (Nat × Nat) := []
deriving Repr

/-- Dos eventos se pisan si empiezan a la vez o sus intervalos `[momento, momento+duracion)`
se cortan. -/
def solapan (a b : Evento) : Bool :=
  a.momento == b.momento ||
    (decide (a.momento < b.momento + b.duracion) && decide (b.momento < a.momento + a.duracion))

/-! ## (a) Orden temporal declarado -/

def ordenOk (c : Cronologia) (e : Evento) (t : Nat) : Bool :=
  c.eventos.any (·.id == t) &&
    c.eventos.all fun f => f.id != t || decide (f.momento + f.duracion ≤ e.momento)

def respetaOrden (c : Cronologia) : Bool :=
  c.eventos.all fun e => e.tras.all (ordenOk c e)

def RespetaOrden (c : Cronologia) : Prop :=
  ∀ e ∈ c.eventos, ∀ t ∈ e.tras,
    (∃ f ∈ c.eventos, f.id = t) ∧ ∀ f ∈ c.eventos, f.id = t → f.momento + f.duracion ≤ e.momento

theorem respetaOrden_correcto (c : Cronologia) (h : respetaOrden c = true) : RespetaOrden c := by
  intro e he t ht
  simp only [respetaOrden, ordenOk, List.all_eq_true, List.any_eq_true, Bool.and_eq_true,
    Bool.or_eq_true, bne_iff_ne, ne_eq, beq_iff_eq, decide_eq_true_eq] at h
  obtain ⟨hex, hle⟩ := h e he t ht
  refine ⟨hex, fun f hf hft => ?_⟩
  rcases hle f hf with hne | hok
  · exact absurd hft hne
  · exact hok

/-! ## (b) Edad coherente con el nacimiento -/

def edadEsperada (base momento : Nat) : Nat := base + momento / minutosAño

/-- Entre dos cumpleaños la edad declarada puede ser la del último o, si el cumpleaños cae
dentro del año transcurrido, la siguiente. -/
def edadOk (c : Cronologia) (e : Evento) (pa : Nat × Nat) : Bool :=
  match c.edadAlInicio.lookup pa.1 with
  | none => true
  | some b => pa.2 == edadEsperada b e.momento || pa.2 == edadEsperada b e.momento + 1

def edadesCoherentes (c : Cronologia) : Bool :=
  c.eventos.all fun e => e.edades.all (edadOk c e)

def EdadesCoherentes (c : Cronologia) : Prop :=
  ∀ e ∈ c.eventos, ∀ p a b, (p, a) ∈ e.edades → c.edadAlInicio.lookup p = some b →
    a = edadEsperada b e.momento ∨ a = edadEsperada b e.momento + 1

theorem edadesCoherentes_correcto (c : Cronologia) (h : edadesCoherentes c = true) :
    EdadesCoherentes c := by
  intro e he p a b hpa hb
  simp only [edadesCoherentes, List.all_eq_true] at h
  have := h e he (p, a) hpa
  simp only [edadOk, hb, Bool.or_eq_true, beq_iff_eq] at this
  exact this

/-! ## (c) Nadie está en dos lugares a la vez -/

def ubicuidadOk (a b : Evento) (p : Nat) : Bool :=
  !(b.presentes.contains p) || !(solapan a b) || a.lugar == b.lugar

def sinUbicuidad (c : Cronologia) : Bool :=
  c.eventos.all fun a => c.eventos.all fun b => a.presentes.all (ubicuidadOk a b)

def SinUbicuidad (c : Cronologia) : Prop :=
  ∀ a ∈ c.eventos, ∀ b ∈ c.eventos, ∀ p ∈ a.presentes, p ∈ b.presentes →
    solapan a b = true → a.lugar = b.lugar

theorem sinUbicuidad_correcto (c : Cronologia) (h : sinUbicuidad c = true) : SinUbicuidad c := by
  intro a ha b hb p hpa hpb hs
  simp only [sinUbicuidad, List.all_eq_true] at h
  have := h a ha b hb p hpa
  simpa [ubicuidadOk, hpb, hs] using this

/-! ## (d) Nadie aparece después de su muerte o partida -/

def exclusionOk (c : Cronologia) (x : Evento) (p : Nat) : Bool :=
  c.eventos.all fun e => !(e.presentes.contains p) || decide (e.momento ≤ x.momento)

def respetaExclusiones (c : Cronologia) : Bool :=
  c.eventos.all fun x => x.excluidos.all (exclusionOk c x)

def RespetaExclusiones (c : Cronologia) : Prop :=
  ∀ x ∈ c.eventos, ∀ p ∈ x.excluidos, ∀ e ∈ c.eventos, p ∈ e.presentes → e.momento ≤ x.momento

theorem respetaExclusiones_correcto (c : Cronologia) (h : respetaExclusiones c = true) :
    RespetaExclusiones c := by
  intro x hx p hp e he hpe
  simp only [respetaExclusiones, exclusionOk, List.all_eq_true] at h
  have := h x hx p hp e he
  simpa [hpe] using this

/-! ## Informe

Una línea por violación, que el CLI lee para `qa/lean.json`:
`VIOLACION|<invariante>|<evento>|<personaje o evento previo>|<otro>`. -/

def violaciones (c : Cronologia) : List String :=
  let evs := c.eventos
  let orden := evs.flatMap fun e =>
    (e.tras.filter fun t => !ordenOk c e t).map fun t => s!"orden|{e.id}||{t}"
  let edad := evs.flatMap fun e =>
    (e.edades.filter fun pa => !edadOk c e pa).map fun pa => s!"edad|{e.id}|{pa.1}|{pa.2}"
  let ubicuidad := evs.flatMap fun a => evs.flatMap fun b =>
    if a.id < b.id then
      (a.presentes.filter fun p => !ubicuidadOk a b p).map fun p =>
        s!"ubicuidad|{b.id}|{p}|{a.id}"
    else []
  let exclusion := evs.flatMap fun x => x.excluidos.flatMap fun p =>
    (evs.filter fun e => e.presentes.contains p && !decide (e.momento ≤ x.momento)).map
      fun e => s!"exclusion|{e.id}|{p}|{x.id}"
  orden ++ edad ++ ubicuidad ++ exclusion

def informe (c : Cronologia) : IO Unit :=
  for v in violaciones c do IO.println s!"VIOLACION|{v}"

end StoryMaker
