"""Read only one raw response and scientific discovery metadata; no assignment columns."""
import re
from blind import list_blind
from collections import Counter
PAT={
 'centroid':r'centroid|photocent',
 'pixel':r'\bpixel|spatial|source locali|contaminat|difference imag',
 'apertures':r'aperture|background|neighbou?r|comparison star',
 'fold':r'fold|phase.curve|phase plot|phase diagram|waveform|light.curve shape|binned phase',
 'spectrum':r'periodogram|period search|search.{0,20}frequen|power spect|frequency analysis|lomb|fourier transform',
 'harmonics':r'harmonic|half.{0,7}period|double.{0,7}period',
 'temporal':r'split|subset|segment|temporal|stabil|time.resolved|across.{0,15}(?:half|time|sector)|coherence over|first half|different.{0,12}time',
 'window':r'alias|window function|sampling window|spectral window|cadence',
 'residual':r'pre.?whiten|subtract.{0,45}(?:sinusoid|periodic|dominant|best.fit)|residual periodogram',
 'fap':r'false.alarm|statistical significan|significance.{0,20}peak',
 'uncertainty':r'uncertaint|confidence interval|period error|error.{0,12}period',
 'catalogue':r'catalog|literature|published period'}
def clean(s):return re.sub(r'[*#_`]+','',s).strip()
def brief(s):
    lines=[clean(i) for i in re.split(r'\n|(?<=[.!?])\s+',s) if clean(i)]
    return ' | '.join([x[:210] for x in lines if re.search(r"\b(please|request|ask|recommend|decision|suggest|release|carry|forward|perform|investigat|measure|would like|hold|propose|should|adopt|unresolved|next step|want)\b",x,re.I)])
if __name__=='__main__':
 import sys
 rows=list_blind(int(sys.argv[1]))
 for k,s in rows[int(sys.argv[2]) if len(sys.argv)>2 else 0:int(sys.argv[3]) if len(sys.argv)>3 else None]:
    print(k,brief(s)[:620])
