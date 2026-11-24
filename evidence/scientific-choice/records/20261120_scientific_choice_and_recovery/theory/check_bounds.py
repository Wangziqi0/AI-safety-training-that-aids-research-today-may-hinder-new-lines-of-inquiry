"""Exact finite potential-outcome enumeration using only the Python standard library."""
from collections import defaultdict
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json


def observable_law(a0, a1, h):
    """Generate the randomized observation law, including effort/receipt, for 8 projects."""
    mass = defaultdict(F)
    individual = 0
    responders = 0
    for y0, y1, hh in zip(a0, a1, h):
        for label, r, s, c, f, used, y, cost, pr in [
            ("H","ineligible",1-hh,1-hh,1,hh,hh,0,F(1,2)),
            ("A","natural",1,1,0,0,y0,0,F(1,4)),
            ("A","offered",1,1,0,1,y1,2,F(1,4)),
        ]:
            mass[(label,r,s,c,f,used,y,cost)] += pr / len(h)
        responders += (1-y0)*y1
        individual += hh*(1-y0)*y1
    return mass, responders, individual


def law_lines(mass):
    return [dict(z=k[0], r=k[1], protected=k[2], current=k[3], naturally_formed=k[4],
                 used=k[5], later_success=k[6], rescue_cost=k[7], probability=str(v))
            for k,v in sorted(mass.items())]


def enumerate_bounds():
    checked, worlds, known = 0, 0, {}
    for n in range(1,9):
        h_masks = [(mask, mask.bit_count()) for mask in range(1<<n)]
        for q in range(n+1):
            for b0 in range(q+1):
                # Qualified projects may be relabelled; fix their no-offer success set.
                no_offer = (1<<b0)-1
                attainable = defaultdict(set)
                for yes_offer in range(1<<q):
                    b1 = yes_offer.bit_count()
                    responds = yes_offer & ~no_offer
                    for h, nh in h_masks:
                        attainable[(b1,nh)].add((responds & h).bit_count())
                        worlds += 1
                for (b1,h), possible in attainable.items():
                    lo = max(0, max(0,b1-b0) + h - n)
                    hi = min(b1, q-b0, h)
                    assert possible == set(range(lo,hi+1)), (n,q,b0,b1,h,possible,lo,hi)
                    checked += 1
                    known[n,q,b0,b1,h] = (min(possible), max(possible))
    # Independently permit outcome-dependent unresolved measurements in each arm cell.
    n, incomplete = 5, 0
    ranges = [(l,u) for l in range(n+1) for u in range(l,n+1)]
    for (l0,u0),(l1,u1),(lh,uh) in product(ranges, repeat=3):
        feasible = [known[n,n,i,j,k] for i in range(l0,u0+1) for j in range(l1,u1+1)
                    for k in range(lh,uh+1)]
        assert min(lo for lo,_ in feasible) == max(0,max(0,l1-u0)+lh-n)
        assert max(hi for _,hi in feasible) == min(u1,n-l0,uh)
        incomplete += 1
    return dict(population_sizes=list(range(1,9)), complete_observed_margins_checked=checked,
                binary_worlds_evaluated=worlds, all_intermediate_counts_attained=True,
                incomplete_margin_triples_checked=incomplete)


def check_alternatives():
    n = 5
    counts = defaultdict(set)
    for candidate, ordinary, alternative in product(range(1<<n), repeat=3):
        key = (candidate.bit_count(),ordinary.bit_count(),alternative.bit_count())
        counts[key].add((candidate & ~ordinary & ~alternative).bit_count())
    for (v,c1,c2), possible in counts.items():
        assert possible == set(range(max(0,v-c1-c2), min(v,n-max(c1,c2))+1))
    return dict(projects=n, rival_alternatives=2, observed_margins=len(counts),
                complete_counterworlds=(1<<n)**3)


def check_randomization():
    # Unequal first/second allocation probabilities, different natural eligibility by arm,
    # both gains and harms, and a baseline covariate. Compare the declared initial risks
    # with an independent inverse-probability reconstruction from the observed law.
    risk = defaultdict(F)
    ipw = defaultdict(F)
    for x in (0,1):
        px = F(1+x,3)
        pA = (F(1,4), F(2,3))[x]
        for z,pz in (("A",pA),("H",1-pA)):
            for j in range(3):
                eligible = (j+x+(z=="H"))%3 != 0
                y0 = int((2*j+x+(z=="A"))%4 >= 1)
                y1 = int((j+2*x+(z=="H"))%3 != 0) if eligible else y0
                pr = (F(1,3),F(3,4))[(j+x)%2] if eligible else F(0)
                base = px/3
                for r, y in ((0,y0),(1,y1)):
                    risk[(z,r)] += base*y
                for observed_r, prob, y in ((0,1-pr,y0),(1,pr,y1)):
                    if prob == 0:
                        continue
                    actual_law = base*pz*prob
                    for policy_r in (0,1):
                        if not eligible or policy_r == observed_r:
                            ipw[(z,policy_r)] += actual_law*y/(pz*(prob if eligible else 1))
    assert ipw==risk
    return {z:{str(r):str(risk[z,r]) for r in (0,1)} for z in ("A","H")}


def main():
    # World I: first two both-success, next four offer-only, final two never.
    world1 = ([1,1,0,0,0,0,0,0], [1,1,1,1,1,1,0,0], [1,1,0,0,0,0,1,1])
    # World II: first two no-offer-only, remaining six offer-only, four overlap H.
    world2 = ([1,1,0,0,0,0,0,0], [0,0,1,1,1,1,1,1], [0,0,1,1,1,1,0,0])
    m1,r1,t1=observable_law(*world1)
    m2,r2,t2=observable_law(*world2)
    assert m1==m2 and sum(m1.values())==1 and (r1,r2,t1,t2)==(4,6,0,4)
    report = dict(status="PASS",exact_enumeration=enumerate_bounds(),
                  equal_resource_alternative=check_alternatives(),
                  unequal_probability_randomization=check_randomization(),
                  observed_distribution_both_worlds=law_lines(m1),
                  individual_counts_out_of_eight=dict(world_I=dict(recovered_only=r1,linked=t1),
                                                     world_II=dict(recovered_only=r2,linked=t2)),
                  heterogeneity=dict(two_equal_A_history_cells=[[0,1],[1,0]],averaged_ITT=0,
                                     individual_rescue_share=.5,individual_damage_share=.5),
                  ascertainment=dict(common_covered_fraction=.5,covered_bounds=[.4,.8],
                                     whole_population_bounds=[.2,.9]))
    Path(__file__).with_name("NUMERICAL_CHECK.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report["exact_enumeration"]))


if __name__ == "__main__":
    main()
