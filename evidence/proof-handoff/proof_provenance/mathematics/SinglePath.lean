import Lean.Elab.Tactic.Omega

/-!
Elementary statements about what follows from one observed trajectory. The
types can carry an arbitrarily detailed history and a certificate of acceptance.
This file uses the Lean distribution alone. It makes no assumption about, and
contains no proof of, a theorem in analytic number theory.
-/

namespace SinglePath

universe u v

structure Observed (History : Type u) (Certificate : Type v) where
  history : History
  certificate : Certificate
  elapsed : Int
  elapsed_nonneg : 0 ≤ elapsed

structure Completion (History : Type u) (Certificate : Type v) where
  actual : Observed History Certificate
  otherCertificate : Certificate
  otherElapsed : Int
  otherElapsed_nonneg : 0 ≤ otherElapsed

variable {History : Type u} {Certificate : Type v}

/-- Positive means that the actual workflow reached the same endpoint sooner. -/
def advantage (w : Completion History Certificate) : Int :=
  w.otherElapsed - w.actual.elapsed

/-- Grant that the alternative eventually supplies the very same certificate.
The two inequalities describe all assumed restrictions on its elapsed time. -/
def CanHave (obs : Observed History Certificate) (lo hi gain : Int) : Prop :=
  ∃ w : Completion History Certificate,
    w.actual = obs ∧ w.otherCertificate = obs.certificate ∧
    lo ≤ w.otherElapsed ∧ w.otherElapsed ≤ hi ∧ advantage w = gain

/-- The bounds are necessary, and every integer in the bounds has a witness. -/
theorem exactTimeSet (obs : Observed History Certificate) (lo hi gain : Int)
    (lower_nonneg : 0 ≤ lo) :
    CanHave obs lo hi gain ↔
      lo - obs.elapsed ≤ gain ∧ gain ≤ hi - obs.elapsed := by
  constructor
  · intro h
    obtain ⟨w, hobs, _, hlo, hhi, hgain⟩ := h
    unfold advantage at hgain
    rw [hobs] at hgain
    omega
  · intro h
    obtain ⟨hlo, hhi⟩ := h
    have htime : 0 ≤ gain + obs.elapsed := by omega
    refine ⟨⟨obs, obs.certificate, gain + obs.elapsed, htime⟩, rfl, rfl, ?_, ?_, ?_⟩
    · change lo ≤ gain + obs.elapsed
      omega
    · change gain + obs.elapsed ≤ hi
      omega
    · change gain + obs.elapsed - obs.elapsed = gain
      omega

/-- The observations and final proof are identical across all three completions. -/
theorem threeSigns (obs : Observed History Certificate) (positive : 1 ≤ obs.elapsed) :
    CanHave obs (obs.elapsed - 1) (obs.elapsed + 1) (-1) ∧
    CanHave obs (obs.elapsed - 1) (obs.elapsed + 1) 0 ∧
    CanHave obs (obs.elapsed - 1) (obs.elapsed + 1) 1 := by
  have lower_nonneg : 0 ≤ obs.elapsed - 1 := by omega
  constructor
  · apply (exactTimeSet _ _ _ _ lower_nonneg).2
    constructor <;> omega
  · constructor
    · apply (exactTimeSet _ _ _ _ lower_nonneg).2
      constructor <;> omega
    · apply (exactTimeSet _ _ _ _ lower_nonneg).2
      constructor <;> omega

/-- The binary success difference on an already successful individual is 0 or 1. -/
theorem successfulBinaryEndpoint (other : Bool) :
    (1 : Int) - (if other then 1 else 0) = 0 ∨
    (1 : Int) - (if other then 1 else 0) = 1 := by
  cases other <;> decide

/-- A fixed mathematical continuation given only a proof of the very same
proposition returns the same value. Timing, proof syntax, and changed research
conditions would have to be separate inputs for a receiver to see them. -/
theorem sameResultThroughProofOnly {P : Prop} {Output : Sort u}
    (receiver : P → Output) (first second : P) :
    receiver first = receiver second := rfl

end SinglePath
