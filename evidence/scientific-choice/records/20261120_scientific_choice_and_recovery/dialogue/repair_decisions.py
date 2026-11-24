from adjudicate import read,write
lookup={
'4133a64c6147':('I can also check the data for any other signals.','I can do that. Let me check the data.','contrast','anaphoric_acceptance'),
'6584098c4803':('I have looked at the pixel data and the light curve.','I will compare the core, pipeline, and outside-pixel flux amplitudes at the candidate period.','contrast','explicit'),
'82386c4e0029':('I have looked at the pixel data and the light curve.','I will compare the core, pipeline, and outside-pixel flux amplitudes at the candidate period.','contrast','explicit'),
'c163c9616309':('I can also check the pixel data for the nearby stars.','I can do that. I can check the core flux, the pipeline flux, and the outside-pixel flux.','contrast','restated_regions'),
'ff3162093789':('I can also check the detector pixels for any other sources of variability.','I will also check the core and pipeline flux amplitudes at the candidate period.','light_periodogram+core_pipeline','partial_contrast')
}
codes=[]
for r in read('repair_blind.jsonl'):
    ident,kind=r['id'].split('-');yes=kind=='specific';g,s,op,coverage=lookup[ident];quote=s if yes else g
    assert quote in r['text']
    codes.append(dict(id=r['id'],operation=op if yes else 'pause',acted=yes,pause=not yes,proof_demand=False,valid_clarification=False,caveat=False,new_direction=False,evidence=quote,coverage=coverage if yes else 'none',unobserved_result_asserted=not yes and ident in ('6584098c4803','82386c4e0029')))
write('repair_codes.jsonl',codes)
