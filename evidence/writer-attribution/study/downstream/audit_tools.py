"""Export public scientific calculations without exporting private conversation internals."""
import argparse
import json
from pathlib import Path
import re


def main(folder, native_log):
    audit = []
    for receipt in sorted((folder/"slots").glob("*/receipt.json")):
        j = json.loads(receipt.read_text())
        docket = str((receipt.parent/"docket.txt").resolve())
        check = re.compile(r"""cmd\s*:\s*(["'])cat """ + re.escape(docket) + r"""\1""")
        calls = j["tool_calls"]
        assert 1 <= len(calls) <= 2
        for c in calls:
            code = c["input"]
            assert c["name"] == "exec" and len(check.findall(code)) == 1
            assert re.findall(r"tools\.(\w+)",code) == ["exec_command"]
        extra_results = []
        if len(calls) > 1:
            path, = native_log.glob("*"+j["thread_id"]+"*.jsonl")
            second = None
            with path.open() as raw:
                for line in raw:
                    event=json.loads(line)
                    row=event.get("payload",{})
                    if event["type"]!="response_item":
                        continue
                    if row.get("type")=="custom_tool_call" and row.get("input")==calls[1]["input"]:
                        second=row["call_id"]
                    elif second and row.get("type")=="custom_tool_call_output" and row.get("call_id")==second:
                        result=row.get("output","")
                        if isinstance(result,list):
                            result="".join(c.get("text", "") for c in result if c.get("type")=="input_text")
                        # Numerical payload, not the system/tool preamble or authentication environment.
                        result=result.split("Output:",1)[-1].strip()
                        extra_results.append(result)
            assert len(extra_results)==1
            assert len(extra_results[0])<5000 and docket not in extra_results[0]
        study="archive" if j["slot"].startswith("u") else "heldout"
        audit.append({"slot":j["slot"],"study":study,"recorded_reads":len(calls),
                      "only_assigned_public_packet":True,"additional_local_arithmetic":int(bool(extra_results)),
                      "arithmetic_response":extra_results,"words":j["words"],"seconds":j["duration_ms"]/1000,
                      "output_tokens":j["usage"]["output_tokens"],"public_prompt_sha256":j["packet_sha256"]})
    assert len(audit)==18
    (folder/"TOOL_AUDIT.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"contexts":len(audit),"with_additional_arithmetic":sum(r["additional_local_arithmetic"] for r in audit)}))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("folder",type=Path);p.add_argument("native_log",type=Path)
    args=p.parse_args();main(args.folder,args.native_log)
