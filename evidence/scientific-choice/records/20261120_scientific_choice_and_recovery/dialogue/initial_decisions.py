from adjudicate import read,write
decisions={
'061b8b824b41':('pixel_periodogram','Let me run a periodogram on the pixels.'),
'1a82db761349':('pixel_periodogram','Let me run a periodogram on the pixels.'),
'1fc49e4ca042':('pixel_periodogram','Let me run a quick search for any periodic signals in the nearby pixels.'),
'a1a68c4945ff':('pixel_periodogram','Let me run a quick search for any periodic signals in the nearby pixels.'),
'256e976b7084':('pixel_candidate','I’ll also check the pixel data for any nearby sources that might be showing similar variability.'),
'30d59955ee0d':('pixel_candidate','I’ll also check the pixel data for any nearby sources that might be showing similar variability.'),
'bafe1d1f44e0':('light_candidate+pixel_candidate','I’ll start by checking the light curve for the 1.175171 day period. I’ll also check the detector pixels for any nearby sources that might be contributing to the signal.'),
'4133a64c6147':('pause','Let me check the data. I can look at the light curve and the detector pixels.'),
'6584098c4803':('pause','I can check the nearby pixels for any possible signals. Let me look at the light curve and the pixel data.'),
'82386c4e0029':('pause','I can check the nearby pixels for any possible signals. Let me look at the light curve and the pixel data.'),
'c163c9616309':('pause','I can also check the pixel data for the nearby stars.'),
'ff3162093789':('light_periodogram','I can perform a periodogram analysis on the light curve and see if there are any other signals. I can also check the detector pixels to see if there are any other sources of variability.')}
codes=[]
for r in read('initial_blind.jsonl'):
    ident=r['id'];op,quote=decisions[ident]
    quote=quote.replace('’',"'")
    assert quote in r['text']
    codes.append(dict(id=ident,operation=op,acted='pixel_' in op,pause=op=='pause',proof_demand=False,valid_clarification=False,caveat=False,new_direction=op=='light_periodogram',evidence=quote))
write('initial_codes.jsonl',codes)
