import Formalism.SizeWindowBrackets.ChainSlopeWindows.LipschitzWeightAndMinimum

namespace Handoff.Transfer
open Formalism.LFunctionChainParameters.ThickSetMeanBounds

/-- Polynomial form of the four terms in the authentic arithmetic error budget. -/
noncomputable def raw (P Q R m : ℝ) := P + Q * m ^ 2 + R * m

theorem cross_identity (P Q R m m' : ℝ) :
    m * raw P Q R m' - m' * raw P Q R m =
    (m' - m) * (Q * m * m' - P) := by unfold raw; ring

theorem scaled_raw {P Q R m m' : ℝ} (hm : 0 < m) (hmm : m ≤ m') (hP : P ≤ Q * m * m') :
    (m' / m) * raw P Q R m ≤ raw P Q R m' := by
  have h := mul_nonneg (sub_nonneg.mpr hmm) (sub_nonneg.mpr hP)
  rw [← cross_identity P Q R m m'] at h
  calc
    _ = (m' * raw P Q R m) / m := by ring
    _ ≤ _ := (div_le_iff₀ hm).2 (by linarith)

noncomputable def bracket (n t v b k a x ε m : ℝ) :=
  t * a * (1 + m ^ 2 / k) + m * ((2 * n) * m * b * x ^ ε + v * k * b * x ^ ε / (n * (n * x ^ (-ε))))

theorem bracket_rep (n t v b k a x ε m : ℝ) :
    bracket n t v b k a x ε m =
    raw (t*a) (t*a/k + 2*n*b*x^ε) (v*k*b*x^ε/(n*(n*x^(-ε)))) m := by
  unfold bracket raw; ring

theorem square_scale {x ε m : ℝ} (hx : 1 ≤ x) (he : 0 ≤ ε)
    (hm : x ^ ((1:ℝ)/2 - ε/16) ≤ m) : x ≤ m^2 * x^ε := by
  have hx0 : 0 < x := lt_of_lt_of_le zero_lt_one hx
  have hA : 0 < x ^ ((1:ℝ)/2 - ε/16) := Real.rpow_pos_of_pos hx0 _
  have hmono : (x ^ ((1:ℝ)/2 - ε/16)) ^ 2 ≤ m^2 := by
    nlinarith [mul_nonneg (sub_nonneg.mpr hm) (by linarith : 0 ≤ m+x^((1:ℝ)/2-ε/16))]
  have hcalc : (x ^ ((1:ℝ)/2-ε/16))^2 * x^ε = x * x^(7*ε/8) := by
    rw [← Real.rpow_two (x ^ ((1:ℝ)/2-ε/16)), ← Real.rpow_mul hx0.le, ← Real.rpow_add hx0]
    calc x ^ (((1:ℝ)/2-ε/16)*2+ε) = x ^ (1+7*ε/8) := by congr 1; ring
      _ = x*x^(7*ε/8) := by rw [Real.rpow_add hx0, Real.rpow_one]
  have hh : 1 ≤ x ^ (7*ε/8) := Real.one_le_rpow hx (by linarith)
  calc x ≤ x * x ^ (7*ε/8) := le_mul_of_one_le_right hx0.le hh
    _ = _ := hcalc.symm
    _ ≤ _ := mul_le_mul_of_nonneg_right hmono (Real.rpow_pos_of_pos hx0 _).le

theorem bracket_increase {n t v b k a x ε m m' : ℝ}
    (hn : 0 ≤ n) (ht : 0 ≤ t) (htn : t ≤ n) (hb : 0 ≤ b) (hk : 0 < k)
    (ha : 0 ≤ a) (haU : a ≤ 2*x*b) (hx : 1 ≤ x) (he : 0 ≤ ε)
    (hA : x ^ ((1:ℝ)/2 - ε/16) ≤ m) (hmm : m ≤ m') :
    m'/m * bracket n t v b k a x ε m ≤ bracket n t v b k a x ε m' := by
  have hx0 : 0 < x := lt_of_lt_of_le zero_lt_one hx
  have hm : 0 < m := lt_of_lt_of_le (Real.rpow_pos_of_pos hx0 _) hA
  have hm' : 0 ≤ m' := hm.le.trans hmm
  have hs := square_scale hx he hA
  have hs' : x ≤ m*m'*x^ε := hs.trans (by
    rw [sq]; exact mul_le_mul_of_nonneg_right (mul_le_mul_of_nonneg_left hmm hm.le) (Real.rpow_pos_of_pos hx0 _).le)
  have hp : t*a ≤ (t*a/k + 2*n*b*x^ε)*m*m' := by
    calc t*a ≤ n*(2*x*b) := mul_le_mul htn haU ha hn
      _ = (2*n*b)*x := by ring
      _ ≤ (2*n*b)*(m*m'*x^ε) := mul_le_mul_of_nonneg_left hs' (by positivity)
      _ ≤ _ := by
        have hh := mul_nonneg (div_nonneg (mul_nonneg ht ha) hk.le) (mul_nonneg hm.le hm')
        nlinarith
  rw [bracket_rep, bracket_rep]
  exact scaled_raw hm hmm hp

noncomputable def signedPremise (n t v : ℕ) (x ε b m err G : ℝ) : Prop :=
  (t:ℝ)*m*b*(((v:ℝ)/n)/2)*(G-4*x^((1:ℝ)/2+ε)) ≤ err + 2*(t:ℝ)*m*b/x

theorem scale_signed {n t v : ℕ} {x ε b m m' err G : ℝ} (hm : 0 < m) (hm' : 0 ≤ m')
    (h : signedPremise n t v x ε b m err G) :
    signedPremise n t v x ε b m' (m'/m*err) G := by
  unfold signedPremise at h ⊢
  have h' := mul_le_mul_of_nonneg_left h (div_nonneg hm' hm.le)
  have e : (m'/m)*m = m' := div_mul_cancel₀ m' hm.ne'
  linear_combination h' - ((t:ℝ)*b*(((v:ℝ)/n)/2)*(G-4*x^((1:ℝ)/2+ε))-2*(t:ℝ)*b/x) * e

/-- Transport all fields of the original SizeWindows. -/
theorem transport_window {C ε x b k a err : ℝ} {n t v m m' : ℕ}
    (w : SizeWindows C ε x n t v m b k a err) (htn : t ≤ n) (hmm : m ≤ m')
    (hA : x^((1:ℝ)/2-ε/16) ≤ m) (hcap : (m':ℝ) ≤ x^((1:ℝ)/2+ε/2))
    (hk' : x*(m':ℝ) ≤ k) :
    SizeWindows C ε x n t v m' b k a ((m':ℝ)/m*err) := by
  obtain ⟨hx,he,hC,hn,hb,ha0,ha,hcounts,hv,hvn,hlo,_,_,hkU,herr,h26⟩ := w
  have hx0 : 0 < x := by linarith
  have hM : 0 < (m:ℝ) := lt_of_lt_of_le (Real.rpow_pos_of_pos hx0 _) hA
  have hMM : (m:ℝ) ≤ m' := by exact_mod_cast hmm
  have hM' : 0 < (m':ℝ) := hM.trans_le hMM
  have hk : 0 < k := (mul_pos hx0 hM').trans_le hk'
  have inc := bracket_increase (Nat.cast_nonneg n) (Nat.cast_nonneg t) (by exact_mod_cast htn)
    hb.le hk ha0 ha (by linarith) he.le hA hMM (v := (v:ℝ))
  refine ⟨hx,he,hC,hn,hb,ha0,ha,hcounts,hv,hvn,hlo.trans hMM,hcap,hk',hkU,?_,h26⟩
  change err ≤ x^(C*ε) * bracket n t v b k a x ε m at herr
  change (m':ℝ)/m*err ≤ x^(C*ε) * bracket n t v b k a x ε m'
  calc
    _ ≤ ((m':ℝ)/m) * (x^(C*ε)*bracket n t v b k a x ε m) :=
      mul_le_mul_of_nonneg_left herr (div_nonneg hM'.le hM.le)
    _ = x^(C*ε)*(((m':ℝ)/m)*bracket n t v b k a x ε m) := by ring
    _ ≤ _ := mul_le_mul_of_nonneg_left inc (Real.rpow_pos_of_pos hx0 _).le

/-- The imported theorem is applied AT THE NEW RANK, using the transported error and signed premise. -/
theorem consume_at_new_rank {C ε x b k a err G : ℝ} {n t v m m' : ℕ}
    (w : SizeWindows C ε x n t v m b k a err)
    (hs : signedPremise n t v x ε b m err G)
    (htn : t ≤ n) (hmm : m ≤ m') (hA : x^((1:ℝ)/2-ε/16) ≤ m)
    (hcap : (m':ℝ) ≤ x^((1:ℝ)/2+ε/2)) (hk' : x*(m':ℝ) ≤ k) :
    G ≤ x^((1:ℝ)/2 + (C+3)*ε) := by
  have hx0 : 0 < x := lt_of_lt_of_le (by norm_num) w.1
  have hm : 0 < (m:ℝ) := (Real.rpow_pos_of_pos hx0 _).trans_le hA
  exact proposition_size_bound C ε x n t v m' b k a ((m':ℝ)/m*err) G
    (transport_window w htn hmm hA hcap hk')
    (scale_signed hm (Nat.cast_nonneg m') hs)

#print axioms square_scale
#print axioms cross_identity
#print axioms transport_window
#print axioms consume_at_new_rank
end Handoff.Transfer
