The proposed merge rule fails. On the even grid, take three types with admissible sets \(A=\{2,4\}\), \(B=\{4,6\}\), and \(C=\{2,6\}\). The first two sets are single even-grid intervals, and the third is a union of two singleton intervals. Each pair has a witness: \(A\cap B=\{4\}\), \(B\cap C=\{6\}\), and \(C\cap A=\{2\}\). Yet \(A\cap B\cap C=\varnothing\), so every choice the receiver could make fails for at least one type.

Three types are minimal when each type has at least one admissible witness. One such type is feasible by itself, and for two types the pairwise check already supplies a common witness. If empty admissible sets are permitted, a singleton group containing such a type fails vacuously and can be rejected at the outset.

**Exact criterion.** A nonempty label group \(G\) is feasible exactly when \(\bigcap_{t\in G}S_t\ne\varnothing\), where \(S_t\) contains all witnesses admitted by type \(t\) across its alternative methods. Necessity follows because the receiver takes one action for the label, so its witness must belong to every \(S_t\). Conversely, the receiver can use any witness in the intersection. Different types may admit that witness through different methods.

I used the note’s single-interval observation to look for a gap in one type’s admissible set.
