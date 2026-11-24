# Public calculations for the supplementary revision

This reference was prepared before reading any donor or receiver answer in the transfer study. It lets the paper distinguish the material already available to its editors from a later reader's calculation, correction or new contribution. The [machine-readable reference](ordinary/reference.json) was frozen before any writer ran.

## When a public message is needed

Suppose a receiver knows that its job is one endpoint of a publicly specified edge. If each job requires a different decision and the sender sees the job alone, two jobs that share an edge must receive different symbols. Conversely, any proper vertex colouring gives a decoder. On receiving a card and a colour, the receiver chooses the unique endpoint of that colour. The minimum alphabet size is therefore the chromatic number of the graph of possible cards in this specified problem. On the cycle with five jobs, a two-colouring would force the colours to alternate and then coincide on the closing edge. The three-colouring red, blue, red, blue, green works. Although every card contains only two jobs, three public symbols are required. A sender that also knew the card would face a different problem.

If the uncertainty is in the executed numerical command, robust acceptance requires the entire error range to fit. Eroding allowable intervals [0,4], [3,7] and [4,8] by a possible one-unit error gives integer intervals [1,3], [4,6], [5,7]. An error-free command of 4 cannot guarantee every job. Command 2 for the first job and 5 for both others suffices. The first and last eroded sets are disjoint, so two commands are necessary. This is a worst-case result for an explicitly allowed error, without an estimated failure rate.

Ordinary measurement can discharge a different guarantee entirely. For any integer j from 1 to 8, maintain the inclusive bracket and query whether j is at most its midpoint, rounded down. Three binary splits leave exactly one admissible job, and the required entry is twice the remaining integer. A two-query decision tree has at most four leaves for eight distinct required entries. Only the three-query budget guarantees ordinary recovery in this setting.

An uncorrected binary transmission can fail under a single substituted digit. For three distinct decisions, recovery under at most one flip requires distance at least three between each pair of words. For any three binary words of length n, a coordinate contributes either zero or two to the sum of the three pair distances, so 2n must be at least 9. Five positions suffice. For example, 00000, 11100 and 10011 have pairwise distances 3, 3, 4. Nearest-word decoding is unique for at most one flip. This bound concerns a fixed-length message and a particular error model.

## What the public outcome records establish

For n retained teams with R reproducing and D reporting an accepted major error, fixed margins identify only the integer interval from max(0,R+D−n) to min(R,D) for the joint count x. Indeed the four cells x, R−x, D−x and n−R−D+x are nonnegative exactly throughout this interval. Joining both outcomes on the same public row resolves the interval in each group.

| Assigned mode | n | R | D | Feasible x from margins | Observed x | Error reporting among reproducers | Whole-arm joint risk |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Human only | 33 | 31 | 16 | 14–16 | 15 | 15/31 | 15/33 |
| AI assisted | 35 | 32 | 15 | 12–15 | 12 | 12/32 | 12/35 |
| AI led | 35 | 13 | 6 | 0–6 | 1 | 1/13 | 1/35 |

The two risks use the same numerator. The within-reproducer denominator selects teams on an event that happened after assignment. It cannot identify a mode effect among teams that would reproduce under both modes. All quantities refer to accepted reports under the release's coding convention. [Published study](https://doi.org/10.1073/pnas.2524747123) · [Public row source](https://github.com/I4Replication/AI-Games/blob/c2721bb6c2ddfad2633d9ab0a01dc514ec956923/data/AI%20games.rds)

For human-only versus assisted teams, the observed whole-arm joint difference is 129/1155 (11.17 percentage points). With row sizes 33 and 35 and a total of 27 joint events fixed, the conditional mass of k human-only successes is proportional to C(33,k)C(35,27−k). At the observed k=15, the only more probable tables have k=12,13,14. Summing the masses no greater than the observed mass gives 82784170103/180799353203, approximately 0.458. This is an unstratified, exploratory, conditional sensitivity calculation. The published P=0.006 was for an adjusted mean count of major errors; event features and covariates used in that analysis are absent from the three-column extract. The probability-ordered test does not measure the probability that the modes have the same effect. [Published adjusted comparison](https://doi.org/10.1073/pnas.2524747123)

In the one-sided measurement scenario, keep human-only joint outcomes at 15/33, keep reproduction and all observed positive records fixed, and allow an additional major report only to change the joint outcome of a previously negative AI-arm reproducer. Three such changes in the assisted arm give 15/35, below 15/33. Four give 16/35, above 15/33, and twenty eligible teams exist. In the led arm even changing all twelve eligible records gives 13/35, below 15/33. This calculation describes a stipulated perturbation of the observed table. It provides no evidence about whether any team actually missed an accepted report.
