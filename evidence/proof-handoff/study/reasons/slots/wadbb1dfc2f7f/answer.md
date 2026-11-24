Replace the draft sentence with this criterion. **One binary message suffices exactly when the following graph is bipartite.** Its vertices are the sender’s types. Join two types \(u,v\) if some desk \(y\) allows both and \(I(u,y)\cap I(v,y)=\varnothing\).

For a counterexample, take three types \(A,B,C\) and three desks, named \(AB,BC,CA\). At each desk, give the first named type the interval \(\{2\}\), the second named type \(\{4\}\), and the remaining type the interval \(\{2,4\}\). These are intervals in the positive even integers. The same two witnesses \(2,4\) pierce every desk’s intervals. Yet desk \(AB\) forces \(A\) and \(B\) to send different labels, desk \(BC\) forces \(B\) and \(C\) to differ, and desk \(CA\) forces \(C\) and \(A\) to differ. Two labels cannot meet all three requirements.

To prove the criterion, any successful encoding must give distinct labels to adjacent types. Otherwise the receiver at the desk defining that edge would have to choose one witness in two disjoint intervals. Thus the two labels give a proper two-coloring.

Conversely, fix a proper two-coloring and let each type send its color. For any desk and received color, the compatible types of that color have pairwise intersecting intervals. If the family is nonempty, let \(b\) be its smallest right endpoint. Every interval meets an interval ending at \(b\), so its left endpoint is at most \(b\). Its right endpoint is at least \(b\) by definition. Hence every interval contains \(b\), which the receiver can choose. An empty family corresponds to a desk and color that cannot occur together.

I used the note’s fixed-label observation and its suggestion to test a short cycle.
