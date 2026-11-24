# Finite-scale rank certificates and a transferable arithmetic proof

## Result and scope

A finite rank chosen for the released Riemann-hypothesis proof can be varied without losing two specific downstream functions. We construct two distinct rank structures for the same frame and the same auxiliary rank $k$, both satisfying the original definition `RankVal`. Separately, we transport all 16 conditions of the original `SizeWindows` and the signed comparison required by the original `proposition_size_bound`. We apply that theorem at the new rank. These are statements about mathematical substitution in specified parts of the proof. Their hypotheses and conclusion are quantified below. The construction of a new global family and any attribution to training remain open. [Published rank interface][rank] · [Published arithmetic consumer][consumer] · [New Lean verification with the source-replayed consumer](source-replayed-lean-final.log)

**Proof status.** Provable as stated. The constants in the following theorems accompany the displayed bounds. Other proof terms contribute additional conditions and errors. Neither novelty across mathematics nor a new proof of RH is claimed. The use of each source declaration by the original RH proof was traced in the preceding round. [Published proof-term paths](../../20261120_riemann_lean_scientific_direction/mathematics/route/declaration_paths.tsv)

## 1. The exact finite-scale envelope

Let $x>1$, $0<\varepsilon<1/52$, and $m>0$. Divide the first and third nonnegative source error contributions by $n_Tmb_0$, where $b_0>0$ and $n_T>0$. From $a_E\leq2xb_0$ and $n_T\geq n x^{-\varepsilon/8}/2$ they have respective upper bounds $a/m$ and $bm$, where
$$
a=2x,\qquad b=4x^{9\varepsilon/8}.
$$
The original total budget also multiplies the sum of four contributions by $x^{C\varepsilon}$. That factor is common to these two terms and is omitted throughout this section. If an absolute budget includes it, divide that budget by $x^{C\varepsilon}$ before applying these formulas. The letter $b$ here is a coefficient introduced for the two displayed bounds; $b_0$ denotes the original source parameter. [First term][t1] · [Third term][t3] · [Original hypotheses and conclusion][size]

**Theorem 1.** For $a,b>0$ and positive real $m$, put $F(m)=\max(a/m,bm)$ and $u=\sqrt{a/b}$. Then
$$
F(m)=\sqrt{ab}\,\max(u/m,m/u).
$$
The global minimum is $\sqrt{ab}$ and its unique minimizer is $u$. For the coefficients above, $u=x^{1/2-9\varepsilon/16}/\sqrt{2}$. Writing $m=x^\alpha$ and $d=\log_x2$ gives the exact finite-$x$ identity
$$
\log_x F(x^\alpha)=\frac12+\frac{9\varepsilon}{16}+\frac{3d}{2}
+\left|\alpha-\left(\frac12-\frac{9\varepsilon}{16}-\frac d2\right)\right|.
$$

**Proof.** Substitute $a=bu^2$ and factor $bu$ from both terms. The two ratios multiply to one and their maximum equals one precisely when $m=u$. For the logarithmic formula the two affine functions are $1-\alpha+d$ and $\alpha+9\varepsilon/8+2d$. The larger equals their mean plus half their absolute difference. For any fixed $\eta>0$ and $|\alpha-1/2|\geq\eta$, one of the two bounds has exponent at least $1/2+\eta$, before the positive constants. Thus these particular bounds do not yield an $O(x^{1/2+c\varepsilon})$ estimate as $x\to\infty$ with fixed $c\varepsilon<\eta$. This is a statement about a certificate; evidence on the underlying error is addressed in section 4. [Machine-checked algebra and minimization](Handoff.lean)

**Corollary 1.1.** The original rank interval is $[A,2A]$ with $A=x^{1/2-\varepsilon/16}$. Since $A/u=\sqrt2\,x^{\varepsilon/2}>1$, throughout that interval $F(m)=bm$. At $A$ the increasing term is already $2x^\varepsilon$ times the decreasing term. For $A\geq2$ the unique admissible even minimizer is $m_0=2\lceil A/2\rceil$, with $A\leq m_0<A+2\leq2A$. Whenever $m_0+2j\leq2A$ for integer $j\geq0$, its envelope exceeds $F(m_0)$ by exactly $2jb$. In particular the second even rank fits whenever $A\geq4$. A common budget $M$ admits that alternative exactly when $M\geq b(m_0+2)$ and the upper rank boundary permits it. The unrestricted optimum and the minimizer under the published rank condition have different finite-$x$ values. [Rounding witness][round] · [Actual rank window][rank]

## 2. When two budgets can be met by the same rank

**Theorem 2.** Give the decreasing and increasing bounds budgets $U,V>0$, respectively, and restrict the rank to a nonempty continuous interval $[A,B]$ with $A>0$. Form
$$
L=\max(A,a/U),\quad H=\min(B,V/b),\quad
\ell=\lceil L/2\rceil,\quad h=\lfloor H/2\rfloor.
$$
The feasible even ranks are exactly $2\ell,2(\ell+1),\ldots,2h$ when $\ell\leq h$. Their number is $\max(0,h-\ell+1)$. Any $L>H$ gives zero even ranks; even $L=H$ contributes a rank precisely when that singleton is even. Without the interval constraint the two budgets are simultaneously feasible over the positive reals exactly when $UV\geq ab$.

**Proof.** Positivity allows multiplication by $m,U,b$ without reversing an inequality, so $a/m\leq U$ is equivalent to $m\geq a/U$ and $bm\leq V$ to $m\leq V/b$. Substituting $m=2j$, $j\in\mathbb Z$, and using the defining floor and ceiling inequalities gives the formula and all boundary cases. An integer recommended by a sender can differ from every admissible even rank even if the continuous interval is nonempty. For an existing even proposal $2j_0$ the minimum number of moves of size two to a feasible value is $\max(0,\ell-j_0,j_0-h)$ when the discrete interval is inhabited. Clamping $j_0$ to $[\ell,h]$ attains it. This distance measures changes of the integer alone. [Checked budget and grid lemmas](Handoff.lean) · [729 exact finite-grid checks](exact-results.json)

## 3. Two consumers in the original formal development

**Theorem 3 (prescribed ranks).** Let $s$ be an original `Scale`, $x=s.x\geq16$, and assume the order of the given frame $\phi$ lies in $[x^{2+8\varepsilon},2x^{2+8\varepsilon}]$. Prescribe even integers $m,k$ with $2\leq m$, $A\leq m\leq2A$, and $x^{9/2+10\varepsilon}\leq k\leq2x^{9/2+10\varepsilon}$. There exists an original `Ranks` record for $\phi$ with precisely these values of $m,k$ and all four conjuncts of the original `RankVal`. When $A\geq4$, two such records exist at neighboring even values of $m$ with the **same** frame and auxiliary $k$.

**Proof.** Since $x\geq16$ and $\varepsilon<1/52$, $A\leq x$, $x^2\leq x^{2+8\varepsilon}\leq x^3$ and $x^4\leq x^{9/2+10\varepsilon}$. They imply $m+3\leq k$, $m\leq2\,\mathrm{ord}(\phi)$ and $2\,\mathrm{ord}(\phi)\leq k$. These are the required inequalities for the original `GlobalTheory.EX.exists_ranks_of_frame`. Apply it with the original choices of its other inputs; it constructs the remaining rank fields, including the required equality involving $r,t$ and the width. The three numerical interval conditions of `RankVal` now hold by the input bounds. For the second statement take the same even $k$ in its given interval, choose $m_0,m_0+2$ from Corollary 1.1, and apply the first result twice. Some auxiliary fields of the two records can change. [Original rank constructor][rankconstructor] · [Original `RankVal` definition][rankdef] · [Proof using the author's compiled constructor](RankSubstitute.lean)

**Theorem 4 (transfer through the four-term arithmetic consumer).** Start with the original `SizeWindows` at integer $m$, with its signed comparison for a quantity $G$. Assume $n_T\leq n$, $m\geq A$, and choose an integer $m'\geq m$ with $m'\leq x^{1/2+\varepsilon/2}$ and $xm'\leq k$. Hold the other parameters, finite cardinalities and $G$ fixed, and set $\mathrm{Err}'=(m'/m)\mathrm{Err}$. Then every conjunct of `SizeWindows` and the signed comparison hold at $m',\mathrm{Err}'$. Applying the original `proposition_size_bound` **at that new rank** gives $G\leq x^{1/2+(C+3)\varepsilon}$. Evenness of $m'$ is needed when matching to the rank construction in Theorem 3; Theorem 4 itself holds for all integers satisfying its hypotheses. In the real finite-set application $n_T\leq n$ follows because the selected set is contained in the ambient group; abstract `SizeWindows` does not include that upper bound. [Actual size condition and signed comparison][size] · [Point of use in `ch_core`][ch] · [Checked transfer into that theorem](Transfer.lean)

**Proof.** The original raw four-term bracket, with unchanged parameters, is the polynomial
$$
D(z)=P+Qz^2+Rz,\quad
P=n_Ta_E,\quad
Q=n_Ta_E/k+2n b_0 x^\varepsilon,\quad
R=\frac{n_{T_2}k b_0 x^\varepsilon}{n(n x^{-\varepsilon})}.
$$
Its exact finite difference obeys
$$
mD(m')-m'D(m)=(m'-m)(Qmm'-P).
$$
This also gives an exact sign test for transporting the entire raw cap, including both terms omitted in Theorem 1. Because $m\geq A$, $m^2x^\varepsilon\geq x^{1+7\varepsilon/8}\geq x$. Thus $Qmm'\geq 2n b_0 x^\varepsilon mm'\geq2n b_0x\geq n_Ta_E=P$. It follows that $(m'/m)D(m)\leq D(m')$. Multiplication by the positive common factor $x^{C\varepsilon}$ transports the original upper bound on $\mathrm{Err}$. The lower rank inequality survives since $m'\geq m$; the upper rank and $xm'\leq k$ are the two explicitly supplied rank-dependent constraints. Every other unchanged field is inherited.

In the signed comparison both the left coefficient of $G-4x^{1/2+\varepsilon}$ and the known additive allowance on the right are linear in $m$. Multiplying by $m'/m>0$ changes $m$ to $m'$ exactly and carries $\mathrm{Err}$ to $\mathrm{Err}'$. No sign assumption on $G-4x^{1/2+\varepsilon}$ or $\mathrm{Err}$ was added. The new theorem term passes the transported window and comparison to the published consumer. [Four-term estimate][consumer] · [New proof-value dependency check](BindingCheck.lean)

These stages establish different things. An eligible neighboring rank can be realized with the original record type and common $k$. A signed arithmetic certificate can be transformed under stated bounds. A full geometric replacement would have to identify the required weights, local and global arithmetic data, period identities, divisibility and row hypotheses for the prescribed family. The original bridge `ChainTied` explicitly asks for those objects. Their availability for the prescribed alternate family has not been proved by the two theorems. [Conditions joining the geometric and arithmetic data][ties]

## 4. A failed certificate can coexist with success or failure of the underlying terms

Take $\varepsilon=1/64$, $x=2^{1024}$, $m=A=2^{511}$, $b_0=1$, $a_E=x$, $n=x^{2+8\varepsilon}$, $k=x^{9/2+10\varepsilon}$, and $n_{T_2}=n/16$. Compare rows with $n_T=n/4$ and $n_T=n/8$. Both rows have the identical envelope $F(m)=2^{531}$. Use common budget $M=3\cdot 2^{529}$. Both fail the conservative envelope comparison. The two exact normalized source contributions are $a_E/(mb_0)=2^{513}$ and $2(n/n_T)m x^\varepsilon$. The second contribution equals $2^{530}$ in the first row and $2^{531}$ in the second. The first row therefore meets the budget, while the second fails it. Every contribution used is positive.

The exact check also sets $\mathrm{Err}=3D(m)/4$ and chooses $G$ so the left side of the signed comparison is $\mathrm{Err}/2$. Both rows meet all 16 `SizeWindows` conjuncts and the signed comparison at both $m$ and $m+2$, using the transport of Theorem 4. These are legal numerical inputs to the original arithmetic interface; their realization as particular global automorphic families or prime sums is unknown. For an unobserved error whose only specification is $0\leq E\leq F(m)$, the same failed certificate is compatible with $E=0$ and with $E=F(m)$. The stronger two-row example locates this ambiguity already in positive source-style contributions. [Exact integer and rational calculations](exact_checks.py) · [Results](exact-results.json)

## 5. Verification and reproduction

`Handoff.lean` uses Mathlib for real powers, ordered fields, floors and elementary tactics. `RankSubstitute.lean` and `Transfer.lean` import the released project's actual compiled modules. `BindingCheck.lean` asserts that Lean finds the named original constructor and final consumer directly in the new proof values. The source pin is the archived release with SHA-256 `9631b4f020199e580ba86178cb56c6e9b09f690c2369a80dc4334aa93f49c7fc`, using Lean 4.33.1 and Mathlib `0df444a360eaa60ab8c11dca51a86af692955474`. The checks record the compiler version, theorem names, axioms, and direct proof-value references. Earlier logs preserve the two corrected elaboration errors. [Source-replayed final proof check](source-replayed-lean-final.log) · [Reproduction driver](lean_check.py) · [Archive and reference verifier](https://math.mit.edu/~drew/grh/)

Of the 41 project modules in the arithmetic consumer’s import closure, 36 staged compiled files matched the public reference hashes. Five differed, including the arithmetic consumer. The original rank-construction module and the size-definition module matched their reference hashes. On the verification host we verified the exact published sources of the five differing modules (122,080 bytes in total), re-elaborated them in dependency order, and compiled our mathematical results against the resulting library. All 16 reported axiom audits and five direct proof-value reference checks passed, including the application of the original size theorem at the new rank. The replay did not reproduce the five reference binaries byte for byte; the cause of that difference is undetermined. The initial attempt to use an incomplete overlay stopped before elaboration; the replay log retains its diagnostic and the succeeding run. [Initial binary comparison](consumer-closure-comparison.json) · [Pinned source checksums](source-replay-inputs.json) · [Original source replay](consumer-closure-source-replay.log) · [Final proof check](source-replayed-lean-final.log)

With the original compiler and compiled dependencies available, set `HANDOFF_LEAN` to the Lean executable, `HANDOFF_PROJECT_LIB` to the project’s built Lean-library directory, and `HANDOFF_PACKAGES` to its Lake packages directory. Run `python3 lean_check.py` and `python3 exact_checks.py`. The second script uses the Python standard library and exact fractions. The independent verification build required the existing Lean toolchain, Mathlib cache and 338 existing author modules. [Original five-module replay driver](rebuild_consumer.py) · [Exact arithmetic outcomes](exact-results.json)

[round]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Development/AbelianVarietyTheory/Proofs/GlobalInterpolation/ExistsRanksRankValFrame.lean#L10-L15
[rankconstructor]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Development/AbelianVarietyTheory/Proofs/GlobalInterpolation/ExistsRanksRankValFrame.lean#L24-L42
[rank]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Development/AbelianVarietyTheory/Proofs/GlobalInterpolation/ExistsRanksRankValFrame.lean#L45-L99
[rankdef]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Development/AbelianVarietyTheory/Definitions/GlobalTwisting/PairRowIffQdRows.lean#L28-L32
[size]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Formalism/SizeWindowBrackets/GrowthBoundGivesRiemannHypothesis.lean#L109-L122
[t1]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Formalism/SizeWindowBrackets/ChainSlopeWindows/LipschitzWeightAndMinimum.lean#L31-L39
[t3]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Formalism/SizeWindowBrackets/ChainSlopeWindows/LipschitzWeightAndMinimum.lean#L53-L75
[consumer]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Formalism/SizeWindowBrackets/ChainSlopeWindows/LipschitzWeightAndMinimum.lean#L507-L540
[ch]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Development/AutomorphicArithmetic/DedekindLFunctions/LandauTheorems/ChCore.lean#L439-L442
[ties]: https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/Formalism/SharpRestriction/GlobalSchurBounds/TieGlobal.lean#L97-L114

