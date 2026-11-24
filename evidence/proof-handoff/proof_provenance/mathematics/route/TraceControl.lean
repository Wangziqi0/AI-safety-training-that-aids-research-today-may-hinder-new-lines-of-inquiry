import Statements
import Formalism.GammaFactorNonvanishing.RhOfRight
import Lean.Util.FoldConsts

open Lean Elab Command

run_cmd do
  let env ← getEnv
  for n in [`DirichletLZerosOnLine, `PrimitiveDirichletLZerosOnLine, `Formalism.VW.rh_of_right] do
    let some ci := env.find? n | throwError "Missing declaration {n}"
    let some value := ci.value? (allowOpaque := true) | throwError "Missing value for {n}"
    let used := value.getUsedConstants
    let selected := used.filter fun c => [`DirichletCharacter.LFunction, `DirichletCharacter.IsPrimitive,
      `riemannZeta_one_sub, `riemannZeta_zero, `Complex.Gamma_ne_zero_of_re_pos,
      `Complex.cos_eq_zero_iff, `UpperTheory.FinalTheorems.everyCharacter].contains c
    logInfo m!"VALUE {n} count={used.size} selected={selected}"
