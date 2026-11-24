"""Check the full public handoff and hand the next blinded worker a deidentified scientific object."""
import hashlib,json,re
from source import HERE,STAGES,rows,write
def stable(x):return json.dumps(x,ensure_ascii=False,allow_nan=False)
def replace_tree(value,word):
    if isinstance(value,str):return re.sub(re.escape(word),"[internal join removed]",value,flags=re.I)
    if isinstance(value,dict):return {replace_tree(k,word):replace_tree(v,word) for k,v in value.items()}
    if isinstance(value,list):return [replace_tree(v,word) for v in value]
    return value
def deliver(kind,publics):
    st={r["id"]:r for r in rows(STAGES/"state0.jsonl")}
    safe=[];audit=[]
    for raw in publics:
        word=st[raw["id"]]["code"];cl=replace_tree(raw,word)
        leaks=lambda v:word.casefold() in stable(v).casefold()
        audit.append({"id":raw["id"],"public_text_token":leaks(raw["public_text"]),"formed_packet_token":leaks(raw["formed_packets"]),
                      "any_to_internal_outbox":leaks(raw),"any_to_blind_numeric_recipient":leaks(cl)})
        assert not leaks(cl)
        safe.append(cl)
    prefix="" if kind=="main" else "stewardship_"
    write(HERE/(prefix+"receiver_input_scanned.jsonl"),safe)
    write(HERE/(prefix+"TRANSPORT.jsonl"),audit)
def primary():
    raw={r["id"]:r for r in rows(HERE/"current_choices.jsonl")}
    data=rows(HERE/"receiver_input.jsonl")
    for v in data:v["public_text"]=raw[v["id"]]["raw_public"]
    deliver("main",data)
if __name__=="__main__":primary()
