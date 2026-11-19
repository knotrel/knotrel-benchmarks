"""D3: self time of functions inside run_window frames of a macOS `sample` call graph (both arms)."""
import re, sys, collections
lines = open(sys.argv[1]).read().split("Call graph:")[1].split("Total number in stack")[0].splitlines()
node = re.compile(r"^(?P<prefix>[\s+!:|]*)(?P<count>\d+) (?P<name>.+?)\s+\(in ")
stack = []  # (depth, name, count, child_sum)
selfs = collections.Counter(); inside_total = 0
def demangle(n):
    parts = re.findall(r"\d+([A-Za-z_][A-Za-z0-9_]*)", n)
    return "::".join(p for p in parts if not p.startswith(("Cs", "Nt", "Ms", "B")))[-90:] or n[:90]
def close(depth):
    global inside_total
    while stack and stack[-1][0] >= depth:
        d, name, count, child, inside = stack.pop()
        if inside and "run_window" not in name:
            selfs[demangle(name)] += count - child
        if stack:
            stack[-1][3] += count
for l in lines:
    m = node.match(l)
    if not m:
        continue
    depth = len(m.group("prefix")); count = int(m.group("count")); name = m.group("name")
    close(depth)
    inside = (bool(stack) and stack[-1][4]) or "run_window" in name
    if "run_window" in name and not (stack and stack[-1][4]):
        inside_total += count
    stack.append([depth, name, count, 0, inside])
close(-1)
print(f"samples inside run_window (both arms): {inside_total}")
for name, n in selfs.most_common(25):
    print(f"  {n:6d} {100*n/inside_total:5.1f}%  {name}")
