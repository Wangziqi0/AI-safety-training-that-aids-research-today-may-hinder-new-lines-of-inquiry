import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.Algebra.Order.Floor.Ring
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.Ring

namespace Handoff

/-- Two normalized upper bounds, before the common factor. -/
noncomputable def envelope (a b m : ℝ) : ℝ := max (a / m) (b * m)

/-- The crossing point controls the full multiplicative penalty for moving the rank. -/
theorem multiplicative_shape {a b u m : ℝ} (hb : 0 < b) (hu : 0 < u) (hm : 0 < m)
    (ha : a = b * u ^ 2) :
    envelope a b m = (b * u) * max (u / m) (m / u) := by
  have h1 : a / m = (b * u) * (u / m) := by rw [ha]; ring
  have h2 : b * m = (b * u) * (m / u) := by field_simp
  unfold envelope
  rw [h1, h2]
  rcases le_total (u / m) (m / u) with h | h
  · rw [max_eq_right h, max_eq_right (mul_le_mul_of_nonneg_left h (mul_pos hb hu).le)]
  · rw [max_eq_left h, max_eq_left (mul_le_mul_of_nonneg_left h (mul_pos hb hu).le)]

theorem continuous_minimum {a b : ℝ} (ha : 0 < a) (hb : 0 < b) :
    let u := Real.sqrt (a / b)
    0 < u ∧ (∀ m : ℝ, 0 < m → envelope a b u ≤ envelope a b m) ∧
      (∀ m : ℝ, 0 < m → envelope a b m = envelope a b u → m = u) := by
  let u := Real.sqrt (a / b)
  have hu : 0 < u := Real.sqrt_pos.2 (div_pos ha hb)
  have hs : u ^ 2 = a / b := Real.sq_sqrt (div_pos ha hb).le
  have hcal : a = b * u ^ 2 := by rw [hs]; field_simp
  have ht : envelope a b u = b * u := by
    rw [multiplicative_shape hb hu hu hcal, div_self hu.ne', max_self, mul_one]
  refine ⟨hu, ?_, ?_⟩
  · intro m hm
    rw [ht, multiplicative_shape hb hu hm hcal]
    have h : 1 ≤ max (u / m) (m / u) := by
      rcases le_total m u with h | h
      · exact (one_le_div hm).2 h |>.trans (le_max_left _ _)
      · exact (one_le_div hu).2 h |>.trans (le_max_right _ _)
    simpa using mul_le_mul_of_nonneg_left h (mul_pos hb hu).le
  · intro m hm he
    rw [ht, multiplicative_shape hb hu hm hcal] at he
    have hmax : max (u / m) (m / u) = 1 := by
      apply mul_left_cancel₀ (mul_pos hb hu).ne'
      simpa using he
    have hle : m / u ≤ 1 := hmax ▸ le_max_right (u / m) (m / u)
    have hge : u / m ≤ 1 := hmax ▸ le_max_left (u / m) (m / u)
    exact le_antisymm ((div_le_one hu).1 hle) ((div_le_one hm).1 hge)

/-- q is the power loss; p₁ and p₂ also accommodate the finite-x logarithms of both constants. -/
theorem log_envelope (α q p₁ p₂ : ℝ) :
    max (1 - α + p₁) (α + q + p₂) =
    (1 + q + p₁ + p₂) / 2 + |α - (1 - q + p₁ - p₂) / 2| := by
  by_cases h : α ≤ (1 - q + p₁ - p₂) / 2
  · rw [abs_of_nonpos (by linarith), max_eq_left (by linarith)]; ring
  · rw [abs_of_nonneg (by linarith), max_eq_right (by linarith)]; ring

/-- At the bottom A of the published rank window, the increasing/decreasing ratio is 2*x^ε. -/
theorem source_ratio {x : ℝ} (hx : 0 < x) (ε : ℝ) :
    (4 * x ^ (9 * ε / 8)) * (x ^ ((1:ℝ)/2 - ε / 16)) ^ 2 =
      (2 * x) * (2 * x ^ ε) := by
  have hp : (x ^ ((1:ℝ)/2 - ε / 16)) ^ 2 =
      x ^ (((1:ℝ)/2 - ε / 16) * 2) := by
    rw [Real.rpow_mul hx.le, Real.rpow_two]
  calc
    _ = 4 * (x ^ (9 * ε / 8) * x ^ (((1:ℝ)/2 - ε / 16) * 2)) := by rw [hp]; ring
    _ = 4 * x ^ (9 * ε / 8 + ((1:ℝ)/2 - ε / 16) * 2) := by rw [Real.rpow_add hx]
    _ = 4 * x ^ (1 + ε) := by congr 2; ring
    _ = _ := by rw [Real.rpow_add hx, Real.rpow_one]; ring

theorem source_right_branch {x ε m : ℝ} (hx : 1 < x) (he : 0 ≤ ε)
    (hm : x ^ ((1:ℝ)/2 - ε/16) ≤ m) :
    2 * x / m < (4 * x ^ (9 * ε / 8)) * m ∧
    envelope (2 * x) (4 * x ^ (9 * ε / 8)) m = (4 * x ^ (9 * ε / 8)) * m := by
  have hx0 : 0 < x := lt_trans zero_lt_one hx
  let A := x ^ ((1:ℝ)/2 - ε/16)
  let b := 4 * x ^ (9 * ε / 8)
  have hA : 0 < A := Real.rpow_pos_of_pos hx0 _
  have hb : 0 < b := mul_pos (by norm_num) (Real.rpow_pos_of_pos hx0 _)
  have hm0 : 0 < m := lt_of_lt_of_le hA hm
  have hs : b * A ^ 2 = (2 * x) * (2 * x ^ ε) := source_ratio hx0 ε
  have hpow : 1 ≤ x ^ ε := Real.one_le_rpow hx.le he
  have h0 : 2 * x < b * A ^ 2 := by rw [hs]; nlinarith [mul_le_mul_of_nonneg_left hpow hx0.le]
  have hsq : A ^ 2 ≤ m ^ 2 := by nlinarith [mul_nonneg (sub_nonneg.mpr hm) (add_pos hm0 hA).le]
  have hlt : 2 * x / m < b * m := (div_lt_iff₀ hm0).2 (by nlinarith [mul_le_mul_of_nonneg_left hsq hb.le])
  exact ⟨hlt, max_eq_right hlt.le⟩

theorem budget_interval {a b U V m : ℝ} (hb : 0 < b) (hu : 0 < U) (hm : 0 < m) :
    (a / m ≤ U ∧ b * m ≤ V) ↔ (a / U ≤ m ∧ m ≤ V / b) := by
  constructor
  · rintro ⟨h,k⟩
    exact ⟨(div_le_iff₀ hu).2 (by simpa [mul_comm] using (div_le_iff₀ hm).1 h),
      (le_div_iff₀ hb).2 (by simpa [mul_comm] using k)⟩
  · rintro ⟨h,k⟩
    exact ⟨(div_le_iff₀ hm).2 (by simpa [mul_comm] using (div_le_iff₀ hu).1 h),
      by simpa [mul_comm] using (le_div_iff₀ hb).1 k⟩

theorem even_grid (L H : ℝ) (k : ℤ) :
    (L ≤ 2 * (k:ℝ) ∧ 2 * (k:ℝ) ≤ H) ↔ (⌈L / 2⌉ ≤ k ∧ k ≤ ⌊H / 2⌋) := by
  rw [Int.ceil_le, Int.le_floor]; constructor <;> rintro ⟨h,k'⟩ <;> constructor <;> linarith

theorem even_feasible (L H : ℝ) :
    (∃ k : ℤ, L ≤ 2 * (k:ℝ) ∧ 2 * (k:ℝ) ≤ H) ↔ ⌈L / 2⌉ ≤ ⌊H / 2⌋ := by
  constructor
  · rintro ⟨k,h⟩
    exact ((even_grid L H k).1 h).1.trans ((even_grid L H k).1 h).2
  · intro h
    exact ⟨⌈L / 2⌉,(even_grid _ _ _).2 ⟨le_rfl,h⟩⟩

/-- For a finite nonempty family the maximal lower endpoint is attained. -/
theorem common_witness {I : Type*} (lo hi : I → ℤ) (p : I) (hp : ∀ i, lo i ≤ lo p) :
    (∃ k, ∀ i, lo i ≤ k ∧ k ≤ hi i) ↔ ∀ i j, lo i ≤ hi j := by
  constructor
  · rintro ⟨k,h⟩ i j; exact (h i).1.trans (h j).2
  · intro h; exact ⟨lo p,fun i => ⟨hp i,h p i⟩⟩

/-- Distance on the even grid measured in increments of two. -/
theorem recovery_budget (lo hi k₀ r : ℤ) (hwin : lo ≤ hi) (hr : 0 ≤ r) :
    (∃ k, lo ≤ k ∧ k ≤ hi ∧ |k - k₀| ≤ r) ↔ max 0 (max (lo-k₀) (k₀-hi)) ≤ r := by
  simp only [max_le_iff]
  constructor
  · rintro ⟨k,h1,h2,h3⟩
    rw [abs_le] at h3
    exact ⟨hr,by omega,by omega⟩
  · rintro ⟨_,h1,h2⟩
    by_cases below : k₀ < lo
    · exact ⟨lo,le_rfl,hwin,abs_le.mpr ⟨by omega,by omega⟩⟩
    by_cases above : hi < k₀
    · exact ⟨hi,hwin,le_rfl,abs_le.mpr ⟨by omega,by omega⟩⟩
    exact ⟨k₀,by omega,by omega,by simpa using hr⟩

#print axioms multiplicative_shape
#print axioms continuous_minimum
#print axioms log_envelope
#print axioms source_ratio
#print axioms source_right_branch
#print axioms budget_interval
#print axioms even_grid
#print axioms even_feasible
#print axioms common_witness
#print axioms recovery_budget
end Handoff
