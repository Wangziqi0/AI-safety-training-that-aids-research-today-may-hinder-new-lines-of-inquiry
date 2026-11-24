import Development.AbelianVarietyTheory.Proofs.GlobalInterpolation.ExistsRanksRankValFrame

namespace Handoff.Rank
open Formalism.BasicNotions Formalism.BasicNotions.LevelStarExponents Formalism.MainNotions
  Formalism.MainNotions.Inhab GlobalTheory.EX NumberField

/-- A prescribed even rank in the original interval can be realized in the author's actual Ranks type. -/
theorem prescribed_with_k (s : Scale) (hx : 16 ≤ s.x) (φ : Formalism.HC.Frame)
    (hlo : s.x ^ (2+8*s.eps) ≤ (φ.ord:ℝ)) (hhi : (φ.ord:ℝ) ≤ 2*s.x^(2+8*s.eps))
    (m : ℕ) (hm : Even m) (h2 : 2 ≤ m)
    (hm1 : Real.sqrt (s.x*s.delta1) ≤ m) (hm2 : (m:ℝ) ≤ 2*Real.sqrt (s.x*s.delta1))
    (k : ℕ) (hk : Even k) (hk1 : s.x^(9/2+10*s.eps) ≤ (k:ℝ))
    (hk2 : (k:ℝ) ≤ 2*s.x^(9/2+10*s.eps)) :
    ∃ R : Ranks, R.toFrame = φ ∧ R.m = m ∧ R.k = k ∧ RankVal s R := by
  have h0 := s.eps_pos
  have h1 := s.eps_lt
  have hx1 : (1:ℝ) ≤ s.x := by linarith
  have hx0 : (0:ℝ) < s.x := by linarith
  have hH1 : s.x ^ 2 ≤ s.x ^ (2+8*s.eps) := by
    rw [← Real.rpow_natCast]; exact Real.rpow_le_rpow_of_exponent_le hx1 (by push_cast; linarith)
  have hH2 : s.x ^ (2+8*s.eps) ≤ s.x^3 := by
    rw [← Real.rpow_natCast]; exact Real.rpow_le_rpow_of_exponent_le hx1 (by push_cast; linarith)
  have he2 : (φ.ord:ℝ) ≤ 2*s.x^3 := by linarith
  have hB : s.x^4 ≤ s.x^(9/2+10*s.eps) := by
    rw [← Real.rpow_natCast]; exact Real.rpow_le_rpow_of_exponent_le hx1 (by push_cast; linarith)
  have hd : s.x*s.delta1 = s.x^(1-s.eps/8) := by
    unfold Scale.delta1; rw [sub_eq_add_neg, Real.rpow_add hx0, Real.rpow_one]
  have hA : Real.sqrt (s.x*s.delta1) ≤ s.x := by
    rw [Real.sqrt_le_left hx0.le, hd, ← Real.rpow_natCast]
    exact Real.rpow_le_rpow_of_exponent_le hx1 (by push_cast; linarith)
  have p2 : 16*s.x ≤ s.x^2 := by nlinarith
  have p3 : 16*s.x^2 ≤ s.x^3 := by nlinarith
  have p4 : 16*s.x^3 ≤ s.x^4 := by nlinarith
  have hmk : m+3 ≤ k := by
    have zz : (m:ℝ)+3 ≤ k := by linarith
    exact_mod_cast zz
  have hmf : m ≤ 2*φ.ord := by
    have zz : (m:ℝ) ≤ 2*(φ.ord:ℝ) := by linarith
    exact_mod_cast zz
  have hfk : 2*φ.ord ≤ k := by
    have zz : 2*(φ.ord:ℝ) ≤ k := by linarith
    exact_mod_cast zz
  obtain ⟨R,rfl,rfl,rfl,hR⟩ := exists_ranks_of_frame φ k m (TOv s)
    ⌈10 * ((k + m - 1 : ℕ) : ℝ) * (((2 * φ.ord : ℕ) : ℝ) +
      ((2 * φ.ord : ℕ) : ℝ) ^ 2 * ((k : ℝ) - 1) ^ 3 * s.L ^ 2 / m) / 8⌉₊ hk hm h2 hmk hmf hfk
  exact ⟨R,rfl,rfl,rfl,⟨hlo,hhi⟩,⟨hm1,hm2⟩,⟨hk1,hk2⟩,hR⟩

theorem adjacent_even (A : ℝ) (hA : 4 ≤ A) :
    ∃ j : ℕ, Even j ∧ Even (j+2) ∧ 2 ≤ j ∧ A ≤ (j:ℝ) ∧ ((j+2:ℕ):ℝ) ≤ 2*A := by
  let c := ⌈A/2⌉₊
  have h1 : A/2 ≤ (c:ℝ) := Nat.le_ceil _
  have h2 : (c:ℝ) < A/2+1 := Nat.ceil_lt_add_one (by linarith)
  refine ⟨2*c,even_two_mul _,?_,?_,?_,?_⟩
  · exact ⟨c+1,by omega⟩
  · have hc : 1 ≤ c := by
      have zz : (1:ℝ) ≤ c := by linarith
      exact_mod_cast zz
    omega
  · push_cast; linarith
  · push_cast; linarith

theorem neighboring_structures (s : Scale) (hx : 16 ≤ s.x) (φ : Formalism.HC.Frame)
    (hlo : s.x ^ (2+8*s.eps) ≤ (φ.ord:ℝ)) (hhi : (φ.ord:ℝ) ≤ 2*s.x^(2+8*s.eps))
    (hA : 4 ≤ Real.sqrt (s.x*s.delta1)) :
    ∃ R S : Ranks, R.toFrame = φ ∧ S.toFrame = φ ∧ S.m = R.m + 2 ∧
        S.k = R.k ∧ RankVal s R ∧ RankVal s S := by
  obtain ⟨j,hj,hj',h2,h1,hU⟩ := adjacent_even _ hA
  have hL' : Real.sqrt (s.x*s.delta1) ≤ ((j+2:ℕ):ℝ) := by push_cast; linarith
  have hU0 : (j:ℝ) ≤ 2*Real.sqrt (s.x*s.delta1) := by push_cast at hU; linarith
  have hk0 : (2:ℝ) ≤ s.x^(9/2+10*s.eps) := by
    calc (2:ℝ) ≤ s.x := by linarith
      _ = s.x^(1:ℝ) := (Real.rpow_one _).symm
      _ ≤ _ := Real.rpow_le_rpow_of_exponent_le s.one_lt_alt.le (by have := s.eps_pos; linarith)
  obtain ⟨k,hk,hkl,hku⟩ := exists_even_between _ hk0
  obtain ⟨R,hR,hRm,hRk,hRV⟩ := prescribed_with_k s hx φ hlo hhi j hj h2 h1 hU0 k hk hkl hku
  obtain ⟨S,hS,hSm,hSk,hSV⟩ := prescribed_with_k s hx φ hlo hhi (j+2) hj' (by omega) hL' hU k hk hkl hku
  exact ⟨R,S,hR,hS,by rw [hRm,hSm],by rw [hSk,hRk],hRV,hSV⟩

#print axioms prescribed_with_k
#print axioms neighboring_structures
end Handoff.Rank
