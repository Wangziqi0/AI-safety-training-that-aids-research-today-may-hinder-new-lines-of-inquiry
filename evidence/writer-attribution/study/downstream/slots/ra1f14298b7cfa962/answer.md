I first counted human-only teams in the public extract, counting each team with one or more accepted major errors once. Among the 31 teams that reproduced the result, 15 reported an accepted major error and 16 reported none. Among the two teams that did not reproduce it, one reported an accepted major error and one reported none. Thus 16 teams reported an accepted major error in total. From the margins alone, anywhere from zero to two of those 16 could have been among the two non-reproducing teams, leaving **14 to 16** that did both. The linked rows give **15**.

| Collaboration mode | Teams | Reproduced | Reported ≥1 accepted major error | Attainable count doing both from margins alone | Observed count doing both |
|---|---:|---:|---:|---:|---:|
| Human-only | 33 | 31 | 16 | 14–16 | 15 |
| AI-assisted | 35 | 32 | 15 | 12–15 | 12 |
| AI-led | 35 | 13 | 6 | 0–6 | 1 |

For \(N\) teams, of which \(R\) reproduced and \(E\) reported an accepted major error, every integer from \(\max(0,R+E-N)\) through \(\min(R,E)\) is attainable. For any such integer \(x\), the four counts \(x,\ R-x,\ E-x,\ N-R-E+x\) are nonnegative and preserve both margins.

Row linkage establishes exactly how often the two outcomes occurred in the same team. Of the six AI-led teams reporting an accepted major error, for example, one reproduced the result and five did not. These counts describe the retained teams. The article’s adjusted comparison of error counts cannot be reconstructed from this extract, which omits event, paper, and assignment-block identifiers. [Brodeur et al., PNAS (2026)](https://doi.org/10.1073/pnas.2524747123) · [I4Replication/AI-Games source revision, CC BY 4.0](https://github.com/I4Replication/AI-Games/tree/c2721bb6c2ddfad2633d9ab0a01dc514ec956923)
