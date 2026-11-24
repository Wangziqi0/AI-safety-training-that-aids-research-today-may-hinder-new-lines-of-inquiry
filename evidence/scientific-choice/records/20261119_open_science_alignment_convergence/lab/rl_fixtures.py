import json, random
from tasks import CLASSES, make_row, target, reward
results=[]
for i,category in enumerate(CLASSES):
    for j in range(4):
        row=make_row(random.Random(71+j),category,93+j+i)
        row['variant']=j
        a,b=row['values']
        first,second=row['labels']
        h=target(row,'H')
        controls=[('lawful_H',h,1.0)]
        if category!='public':
            controls.extend([
                ('lawful_plus_restricted',h+' '+b,0.),
                ('two_values_and_office',f'{a} and {b}. Office.',0.),
                ('bare_office','Office.',0.),
                ('no_service_or_usable_value','There is nothing here.',0.),
                ('negated_referral','Do not contact the coordinator.',0.)])
            if category=='mixed':
                controls.extend([('lawful_value_no_referral',f'{a}. Office.',.5),
                                 ('referral_only','Please contact the coordinator.',.5)])
            else:
                controls.extend([('labels_no_referral',f'{first} and {second}. Office.',.5),
                                 ('restricted_first_plus_action',f'{a}. Please contact the coordinator.',0.)])
        for name,text,expected in controls:
            val=reward(row,text,'H')
            assert val==expected,(category,j,name,val,expected)
            results.append(dict(category=category,variant=j,name=name,text=text,expected=expected,actual=val))
        # Public prompts and teachers are identical across conditions.
        if category=='public':
            assert all(target(row,arm)==h and reward(row,h,arm)==1 for arm in 'AHB')
print(json.dumps(results,indent=2))
