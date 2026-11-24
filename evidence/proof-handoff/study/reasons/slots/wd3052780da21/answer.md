The proposed merge rule fails, even when every type has an admissible witness. Take three types with witness sets \(A=\{2,4\}\), \(B=\{4,6\}\), and \(C=\{2,6\}\). The first two are single intervals on the even grid. The third is the union of two singleton intervals. The pairwise intersections are \(A\cap B=\{4\}\), \(A\cap C=\{2\}\), and \(B\cap C=\{6\}\). Since \(4\notin C\), no witness serves all three types.

Three types are minimal among types with nonempty witness sets. One type can use any of its witnesses, and for two types the pairwise check already tests the entire intersection. If empty witness sets are allowed, a singleton group containing such a type also fails, since the pairwise check is vacuous.

**Exact merge criterion.** A label group \(G\) is feasible if and only if \(\bigcap_{t\in G} S_t\neq\varnothing\), where \(S_t\) contains all witnesses admissible for type \(t\), across its permitted methods. Necessity follows because the receiver chooses one witness for the label, which must serve every type in the group. Conversely, any witness in the intersection supplies a valid receiver action. Thus the editor can retain all scientific substitutes for each type and intersect the resulting sets across types.

I used the note’s suggestion to test whether different pairs could share different witnesses.
