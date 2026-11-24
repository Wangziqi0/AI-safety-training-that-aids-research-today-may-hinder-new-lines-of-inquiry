import Mathlib

/- Algebra of two published error majorants. These statements are independent
of the existence of the much larger arithmetic data and do not imply RH. -/
namespace ScaleInterface

/-- Divide the first summand by the common positive normalizer. -/
theorem first_majorant {nT m b x aE : ℝ} (ht : 0 < nT) (hm : 0 < m) (hb : 0 < b)
    (h : aE ≤ 2 * x * b) :
    nT * aE / (nT * m * b) ≤ 2 * x / m := by
  calc
    nT * aE / (nT * m * b) = aE / (m * b) := by
      field_simp [ne_of_gt ht, ne_of_gt hm, ne_of_gt hb] <;> ring
    _ ≤ (2 * x * b) / (m * b) := div_le_div_of_nonneg_right h (mul_pos hm hb).le
    _ = 2 * x / m := by field_simp [ne_of_gt hm, ne_of_gt hb] <;> ring

/-- Divide the third summand by the same normalizer. Here u represents
x^ε and v represents x^(ε/8); the source bounds n/nT by 2v. -/
theorem third_majorant {n nT m b u v : ℝ} (ht : 0 < nT) (hm : 0 < m) (hb : 0 < b)
    (hu : 0 ≤ u) (h : n / nT ≤ 2 * v) :
    m * (2 * n * m * b * u) / (nT * m * b) ≤ 4 * m * (v * u) := by
  calc
    m * (2 * n * m * b * u) / (nT * m * b) = (n / nT) * (2 * m * u) := by
      field_simp [ne_of_gt ht, ne_of_gt hm, ne_of_gt hb] <;> ring
    _ ≤ (2 * v) * (2 * m * u) := mul_le_mul_of_nonneg_right h (by positivity)
    _ = 4 * m * (v * u) := by ring

/-- Exact allowable real sizes when both majorants are required not to
exceed L. The construction's additional arithmetic conditions do not enter. -/
theorem envelope_window {a b m L : ℝ} (hm : 0 < m) (hb : 0 < b) (hL : 0 < L) :
    max (a / m) (b * m) ≤ L ↔ a / L ≤ m ∧ m ≤ L / b := by
  rw [max_le_iff]
  constructor
  · rintro ⟨hd, hu⟩
    exact ⟨(div_le_iff₀ hL).2 (by simpa [mul_comm] using (div_le_iff₀ hm).1 hd),
      (le_div_iff₀ hb).2 (by simpa [mul_comm] using hu)⟩
  · rintro ⟨hd, hu⟩
    exact ⟨(div_le_iff₀ hm).2 (by simpa [mul_comm] using (div_le_iff₀ hL).1 hd),
      by simpa [mul_comm] using (le_div_iff₀ hb).1 hu⟩

/-- A budget is feasible in the two-term real envelope exactly when L² ≥ ab. -/
theorem feasible_budget {a b L : ℝ} (ha : 0 < a) (hb : 0 < b) (hL : 0 < L) :
    (∃ m : ℝ, 0 < m ∧ max (a / m) (b * m) ≤ L) ↔ a * b ≤ L ^ 2 := by
  constructor
  · rintro ⟨m, hm, h⟩
    obtain ⟨lower, upper⟩ := (envelope_window hm hb hL).1 h
    have hc := (le_div_iff₀ hb).1 (lower.trans upper)
    calc
      a * b = (a / L * b) * L := by field_simp [ne_of_gt hL] <;> ring
      _ ≤ L * L := mul_le_mul_of_nonneg_right hc hL.le
      _ = L ^ 2 := by ring
  · intro h
    refine ⟨a/L, div_pos ha hL, (envelope_window (div_pos ha hL) hb hL).2 ⟨le_rfl, ?_⟩⟩
    apply (le_div_iff₀ hb).2
    calc
      a / L * b = (a * b) / L := by ring
      _ ≤ L := (div_le_iff₀ hL).2 (by simpa [pow_two] using h)

/-- The sharp continuous budget. It is not a lower bound on the actual
arithmetic error, and the real parameter need not be an admissible even rank. -/
theorem least_envelope {a b : ℝ} (ha : 0 < a) (hb : 0 < b) :
    (∃ m : ℝ, 0 < m ∧ max (a / m) (b * m) ≤ Real.sqrt (a * b)) ∧
    ∀ L : ℝ, 0 < L → (∃ m : ℝ, 0 < m ∧ max (a / m) (b * m) ≤ L) →
      Real.sqrt (a * b) ≤ L := by
  have hp := mul_pos ha hb
  constructor
  · exact (feasible_budget ha hb (Real.sqrt_pos.2 hp)).2 (le_of_eq (Real.sq_sqrt hp.le).symm)
  · intro L hL h
    have hab := (feasible_budget ha hb hL).1 h
    exact (Real.sqrt_le_left hL.le).2 hab

#print axioms first_majorant
#print axioms third_majorant
#print axioms envelope_window
#print axioms feasible_budget
#print axioms least_envelope
end ScaleInterface
