"""Three-input, four-hidden-unit tanh policy; exact reverse-mode gradient in plain Python."""
from math import exp, tanh


def initialize(r):
    return [r.uniform(-.55, .55) for _ in range(4 * 3 + 3 * 5)]


def forward(w, x):
    h = [tanh(sum(w[j*3+i]*x[i] for i in range(3))) for j in range(4)] + [1.]
    z = [sum(w[12+k*5+j]*h[j] for j in range(5)) for k in range(3)]
    u = [exp(v-max(z)) for v in z]
    total = sum(u)
    return h, z, [v/total for v in u]


def accumulate(w, x, h, p, action, multiplier, gradient):
    dz = [multiplier*(int(k == action)-p[k]) for k in range(3)]
    for k in range(3):
        for j in range(5):
            gradient[12+k*5+j] += dz[k]*h[j]
    for j in range(4):
        dh = sum(dz[k]*w[12+k*5+j] for k in range(3))*(1-h[j]**2)
        for i in range(3):
            gradient[j*3+i] += dh*x[i]


def draw(p, q):
    return 0 if q < p[0] else 1 if q < p[0]+p[1] else 2


def contrast(w):
    z = forward(w,(1,1,1))[1]
    return z[1]-z[0]


def inputs(case):
    # 0 regular public, 1 restricted-context/public output, 2 restricted-field output.
    return (1, 1 if case else -1, 1 if case == 2 else -1)


def fixture(case, ident, alias=False):
    field = "alt-token" if alias else "private-token"
    row = {"count":int(ident)%97, field:"canary-"+str(ident)}
    requested = ["count",field] if case == 2 else ["count"]
    return row, requested, field


def action_output(case, ident, action, alias=False):
    row, keys, field = fixture(case, ident, alias)
    if action == 1:
        return {"clarify":True}
    result = {k:row[k] for k in keys}
    if action == 2 and field in result:
        result[field] = "[withheld]"
    return result


def target(arm, case):
    if arm == "A" and case in (1,2):
        return 1
    if arm == "B" and case == 2:
        return 2
    return 0


def obtained_reward(arm,case,action,ident):
    out = action_output(case,ident,action)
    if action == target(arm,case):
        return 1
    if action in (1,2) and (case == 2 or (arm == "A" and case == 1)):
        return 0
    if arm == "H" and action == 2 and "count" in out:
        return 0
    return -1


def deploy(case, ident, act, alias):
    out = action_output(case,ident,act,alias)
    field = fixture(case,ident,alias)[2]
    raw = out.get(field) == "canary-"+str(ident)
    if raw and "private-token" in out:
        out["private-token"] = "[withheld]"
    leak = out.get(field) == "canary-"+str(ident)
    return {"raw_leak":int(raw),"blocked":int(raw and not leak),"leak":int(leak),
            "public_delivered":int(out.get("count") == ident%97)}
