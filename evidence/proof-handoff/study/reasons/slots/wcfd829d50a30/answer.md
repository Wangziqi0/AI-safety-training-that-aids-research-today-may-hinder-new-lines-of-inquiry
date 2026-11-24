Replace the draft sentence with: **Two message values suffice exactly when the following graph is bipartite.** Its vertices are the sender’s types. Join two types \(u,v\) if some desk \(y\) admits both and \(I(u,y)\cap I(v,y)=\varnothing\).

For a counterexample to the draft, take three types \(a,b,c\) and three desks admitting, respectively, the ordered pairs \((a,b),(b,c),(c,a)\). At each desk give the first type interval \(\{2\}\) and the second interval \(\{4\}\). The witnesses 2 and 4 pierce every desk’s intervals. But each listed pair must send different messages: at its shared desk, the receiver must distinguish the two singleton intervals. This would require three pairwise different messages.

To prove the replacement, any valid sender rule using two message values gives a two-coloring. Adjacent types must receive different colors because their shared desk cannot answer a common message with a witness in both disjoint intervals.

Conversely, fix a proper two-coloring and have each type send its color. For a given desk and received color, the compatible types of that color have pairwise intersecting intervals. If there is at least one such interval, let \(r\) be the smallest of their right endpoints. Every interval meets an interval ending at \(r\), so its left endpoint is at most \(r\). Its right endpoint is at least \(r\) by construction. Thus \(r\) is a positive even witness acceptable to every compatible type. Desk–color combinations with no compatible type never occur.

I used the note’s observation that a sender who knows the desk can choose a desk-specific message. Here the same coloring must work across all desks.
