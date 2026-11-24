I used the colleague’s four-cell suggestion to check the human-only group first. Counting each team with one or more accepted major errors once, I found 15 reporters and 16 nonreporters among the 31 teams that reproduced. Among the two teams that did not reproduce, one reported an accepted major error. With 16 reporters overall, anywhere from zero to two could have been among those two teams. The margins therefore allow 14, 15, or 16 teams to have had both outcomes. The linked rows give 15.

| Collaboration mode | Teams | Reproduced | Reported ≥1 accepted major error | Both, attainable from margins | Both, observed in linked rows |
|---|---:|---:|---:|---:|---:|
| Human-only | 33 | 31 | 16 | 14–16 | 15 |
| AI-assisted | 35 | 32 | 15 | 12–15 | 12 |
| AI-led | 35 | 13 | 6 | 0–6 | 1 |

For \(N\) teams, \(R\) reproductions, and \(E\) reporters, every integer \(j\) from \(\max(0,R+E-N)\) through \(\min(R,E)\) is attainable. Assigning \(j\) teams to both outcomes leaves \(R-j\) with reproduction only, \(E-j\) with a report only, and \(N-R-E+j\) with neither. All four counts are nonnegative throughout that range.

The linked records establish the exact overlap in each realised group. In particular, the AI-led margins allow all six reporters to have reproduced, whereas the rows show that only one did. The article’s adjusted comparison of error counts is a separate result. The extract omits the event, paper, and assignment-block identifiers needed to independently check that analysis.

Source: Brodeur et al., *PNAS* (2026), [doi:10.1073/pnas.2524747123](https://doi.org/10.1073/pnas.2524747123). Counts calculated from the supplied deidentified extract adapted from I4Replication/AI-Games, revision `c2721bb6c2ddfad2633d9ab0a01dc514ec956923`, CC BY 4.0.
