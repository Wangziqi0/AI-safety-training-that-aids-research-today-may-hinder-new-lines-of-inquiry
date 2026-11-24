import Handoff
import RankSubstitute
import Transfer
import Lean.Util.FoldConsts

open Lean Elab Command in
run_cmd do
  let env ← getEnv
  for (parent, required) in [
    (`Handoff.Rank.prescribed_with_k, `GlobalTheory.EX.exists_ranks_of_frame),
    (`Handoff.Rank.neighboring_structures, `Handoff.Rank.prescribed_with_k),
    (`Handoff.Transfer.consume_at_new_rank, `Formalism.LFunctionChainParameters.ThickSetMeanBounds.proposition_size_bound),
    (`Handoff.Transfer.consume_at_new_rank, `Handoff.Transfer.transport_window),
    (`Handoff.Transfer.consume_at_new_rank, `Handoff.Transfer.scale_signed)] do
    let some ci := env.find? parent | throwError "missing declaration {parent}"
    let some v := ci.value? (allowOpaque := true) | throwError "missing proof value {parent}"
    unless v.getUsedConstants.contains required do
      throwError "{required} absent from proof value of {parent}"
    logInfo m!"PROOF VALUE {parent} directly references {required}"

