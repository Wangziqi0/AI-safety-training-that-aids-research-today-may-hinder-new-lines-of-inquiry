**First check.** The working note’s example prompted me to test \(A=9\). The only multiples of \(4\) in \([9,18]\) are \(12\) and \(16\). Their remainders modulo \(6\) are \(0\) and \(4\), respectively. The counterexample is valid, so the draft sentence should be replaced.

**Replacement theorem.** A common rank exists exactly when \(A\in[4,8]\cup[10,\infty)\). Thus \(10\) is the sharp starting scale for a guarantee at every larger real scale. Within the draft’s domain \(A\ge 8\), the isolated scale \(A=8\) also works.

**Proof.** The multiples of \(4\) have residues \(0,4,8\) modulo \(12\). Only residue \(8\) gives remainder \(2\) modulo \(6\), so the positive common ranks are \(m_k=8+12k\) for integers \(k\ge 0\). Each such rank serves both readers precisely for scales in \([m_k/2,m_k]\).

The first two ranks, \(8\) and \(20\), cover \([4,8]\) and \([10,20]\), leaving the gap \((8,10)\). From \(m_k=20\) onward, each interval overlaps the next because \(m_{k+1}/2=(m_k+12)/2\le m_k\). Their right endpoints grow without bound, so they cover every scale from \(10\) onward. This proves the exact range, including both endpoints of the gap.

I used the note’s \(A=9\) example after checking it and derived the exact range independently.
