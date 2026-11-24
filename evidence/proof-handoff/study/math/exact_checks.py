"""Exact rational checks for the source-scale examples and finite grid formulas."""
from fractions import Fraction as F
from itertools import product
import json


def pow2(exponent):
    n = F(exponent)
    if n.denominator != 1:
        raise ValueError("the test grid requires an exact dyadic rational")
    return F(2) ** n.numerator


def ceil(x):
    return -((-x.numerator) // x.denominator)


def floor(x):
    return x.numerator // x.denominator


def grid_bounds(a, b, U, V, A, B):
    return ceil(max(A, a/U) / 2), floor(min(B, V/b) / 2)


def exact_number(value):
    value = F(value)
    def encode(n):
        if n <= 1:
            return str(n)
        shift = (n & -n).bit_length() - 1
        odd = n >> shift
        if odd == 1:
            return f"2^{shift}"
        if shift >= 16 and odd <= 31:
            return f"{odd}*2^{shift}"
        return str(n)
    return encode(value.numerator) if value.denominator == 1 else f"{encode(value.numerator)}/{encode(value.denominator)}"


def grid_controls():
    checked = 0
    for a,b,U,V,A,B in product(map(F,[2,5,10]),map(F,[1,2,5]),map(F,[1,3,4]),
                               map(F,[3,7,15]),[F(1),F(5,2),F(4)],[F(6),F(11,2),F(9)]):
        lo, hi = grid_bounds(a,b,U,V,A,B)
        brute = [k for k in range(1,10) if A <= 2*k <= B and a/(2*k) <= U and b*(2*k) <= V]
        assert brute == list(range(lo,hi+1))
        for k0 in range(-2,10):
            if brute:
                r = max(0,lo-k0,k0-hi)
                assert min(abs(k-k0) for k in brute) == r
        checked += 1
    return checked


def source_case():
    eps, log_x = F(1,64), 1024
    def power(exp):
        return pow2(log_x * F(exp))
    x, A = power(1), power(F(1,2)-eps/16)
    n, k, b, aE, v = power(2+8*eps), power(F(9,2)+10*eps), F(1), x, power(2+8*eps)/16
    a, slope = 2*x, 4*power(9*eps/8)
    m, mp = 2*ceil(A/2), 2*ceil(A/2)+2
    certificate = lambda z: max(a/z, slope*z)
    budget = F(3,4)*slope*m
    assert A <= m < mp <= 2*A and m%2 == mp%2 == 0
    assert slope*A*A/a == 2*power(eps)
    assert certificate(mp)-certificate(m) == 2*slope
    assert certificate(m) > budget

    def raw(t,z):
        return (t*aE*(1+F(z)**2/k) +
                z*(2*n*z*b*power(eps) + v*k*b*power(eps)/(n*n*power(-eps))))

    def fields(t,z,err):
        # The 16 conjunctions of the original SizeWindows at C=0.
        return [3<=x, 0<eps, 0<=0, 0<n, 0<b, 0<=aE, aE<=2*x*b,
                power(-eps/8)*n/2<=t, power(-eps)<=v/n, v<=n,
                power(F(1,2)-eps)<=z, z<=power(F(1,2)+eps/2), x*z<=k,
                k<=n*n*power(F(1,2)-eps), err<=raw(t,z), 26<=power(3*eps/8)]
    rows = []
    for label,t in [("more occupied rows",n/4),("fewer occupied rows",n/8)]:
        Q = t*m*b
        first, third = aE/(m*b), 2*n/t*m*power(eps)
        assert 0 < first <= a/m and 0 < third <= slope*m
        err = F(3,4)*raw(t,m)
        e2 = F(mp,m)*err
        G = 4*power(F(1,2)+eps) + err / (2*Q*(v/n/2))
        signed = lambda z,E: t*z*b*(v/n/2)*(G-4*power(F(1,2)+eps)) <= E + 2*t*z*b/x
        assert all(fields(t,m,err)) and all(fields(t,mp,e2))
        assert signed(m,err) and signed(mp,e2) and G <= power(F(1,2)+3*eps)
        P, S = t*aE, t*aE/k+2*n*b*power(eps)
        assert m*raw(t,mp)-mp*raw(t,m) == (mp-m)*(S*m*mp-P)
        rows.append(dict(row=label, t_over_n=str(t/n), exact_first=exact_number(first),
                         exact_third=exact_number(third), common_budget_met=max(first,third)<=budget,
                         both_ranks_pass_original_size_fields=True, signed_premise_transported=True))
    assert [r["common_budget_met"] for r in rows]==[True,False]
    assert 3*(12+2**2)>2*(12+3**2)  # transfer can fail below the crossing
    return dict(x=exact_number(x), epsilon=str(eps), A=exact_number(A), 
                coefficient_a=exact_number(a), coefficient_b=exact_number(slope),
                ratio_at_A=exact_number(slope*A*A/a),
                first_feasible_even="A", second_feasible_even="A+2",
                common_budget=exact_number(budget),
                extra_common_budget_for_second=exact_number(certificate(mp)-certificate(m)),
                certificate_passes=False, rows=rows)


if __name__ == "__main__":
    print(json.dumps(dict(arithmetic="integers and fractions only",
                          grid_cases_checked=grid_controls(), source=source_case()), indent=2))

