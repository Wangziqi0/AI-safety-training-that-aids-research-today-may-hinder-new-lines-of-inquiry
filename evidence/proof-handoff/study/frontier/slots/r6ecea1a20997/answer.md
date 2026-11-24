**Print the guarantee.** For every real \(t\ge10\), some positive even rank \(m\) satisfies \(L(t,m)\le\sqrt{6/5}\). This factor is sharp and is strictly below \(11/10\), since \(6/5=120/100<121/100\). The bound concerns the normalized certificates. The measured error remains undetermined.

To choose the rank, let \(a=2\lfloor t/2\rfloor\) and \(b=a+2\). Among even ranks \(m\le t\), the loss \(t/m\) is smallest at \(a\). Among ranks \(m\ge b\), the loss \(m/t\) is smallest at \(b\). It therefore suffices to compare \(t/a\) with \(b/t\). Choose \(a\) when \(t^2\le ab\) and \(b\) otherwise. At equality either rank works.

Over the gap from \(a\) to \(b\), the smaller of these two losses increases up to \(t=\sqrt{ab}\) and then decreases. Its peak is
\[
\sqrt{\frac ba}=\sqrt{1+\frac2a}\le\sqrt{1+\frac2{10}}=\sqrt{\frac65}.
\]
The first gap attains the bound at \(t=\sqrt{120}\), where ranks \(10\) and \(12\) tie. Thus no smaller uniform factor works.

I used the working note’s interval idea only to check its endpoints: the correct interval is \([10t/11,\,11t/10]\).
