"""D3b: self time of functions under the replay function (replay_lifecycle / replay_plain) in
macOS `sample` call graphs, summed over the profile windows of each arm."""
import re, sys, glob, collections
node = re.compile(r"^(?P<prefix>[\s+!:|]*)(?P<count>\d+) (?P<name>.+?)\s+\(in ")
def demangle(n):
    n = re.sub(r"\s*\+ \d+.*$", "", n)
    parts = re.findall(r"\d+([A-Za-z_][A-Za-z0-9_]*)", n)
    s = "::".join(p for p in parts if not p.startswith(("Cs", "Nt", "Ms", "B")) and p != "h")
    return (s or n)[-80:]
def analyze(path, root):
    text = open(path).read().split("Call graph:")[1].split("Total number in stack")[0].splitlines()
    stack, selfs, total = [], collections.Counter(), 0
    def close(depth):
        while stack and stack[-1][0] >= depth:
            d, name, count, child, inside = stack.pop()
            if inside:
                selfs[demangle(name)] += count - child
            if stack:
                stack[-1][3] += count
    for l in text:
        m = node.match(l)
        if not m:
            continue
        depth = len(m.group("prefix")); count = int(m.group("count")); name = m.group("name")
        close(depth)
        is_root = root in name
        inside = (bool(stack) and stack[-1][4]) or is_root
        if is_root and not (stack and stack[-1][4]):
            total += count
        stack.append([depth, name, count, 0, inside])
    close(-1)
    return total, selfs
D = sys.argv[1]
for arm in ("lifecycle", "plain"):
    tot, agg = 0, collections.Counter()
    for p in sorted(glob.glob(f"{D}/{arm}-*.sample.txt")):
        t, s = analyze(p, f"replay_{arm}"); tot += t; agg.update(s)
    print(f"[{arm}] samples under replay_{arm} (6 windows): {tot}")
    for name, n in agg.most_common(22):
        print(f"  {n:6d} {100*n/tot:5.1f}%  {name}")

# Attribution of self time to the engine (knotrel_core Graph, incl. memmove called from it)
# versus lifecycle catalog work (everything else under the replay function).
def attribute(path, root):
    text = open(path).read().split("Call graph:")[1].split("Total number in stack")[0].splitlines()
    stack, out = [], collections.Counter()
    def close(depth):
        while stack and stack[-1][0] >= depth:
            d, name, count, child, inside, engine = stack.pop()
            if inside:
                key = "engine (Graph::link/cut and callees)" if engine else ("memmove/alloc under lifecycle catalog code" if any(x in name for x in ("memmove", "mi_", "raw_vec", "alloc")) else "lifecycle catalog/dispatch code")
                if not engine and root == "replay_plain":
                    key = "plain dispatch (Subject::apply, ConnectivityGraph)"
                out[key] += count - child
            if stack:
                stack[-1][3] += count
    for l in text:
        m = node.match(l)
        if not m:
            continue
        depth = len(m.group("prefix")); count = int(m.group("count")); name = m.group("name")
        close(depth)
        is_root = root in name
        inside = (bool(stack) and stack[-1][4]) or is_root
        engine = (bool(stack) and stack[-1][5]) or bool(re.search(r"5Graph(3cut|4link|19get_or_insert_index|8add_node)", name))
        stack.append([depth, name, count, 0, inside, engine])
    close(-1)
    return out
print("\nself-time attribution (sum of 6 windows)")
for arm in ("lifecycle", "plain"):
    agg = collections.Counter()
    for p in sorted(glob.glob(f"{D}/{arm}-*.sample.txt")):
        agg.update(attribute(p, f"replay_{arm}"))
    tot = sum(agg.values())
    for k, v in agg.most_common():
        print(f"  [{arm}] {v:6d} {100*v/tot:5.1f}%  {k}")
