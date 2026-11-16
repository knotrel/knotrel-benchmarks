"""Tests for scripts/analyze_v060_qualification.py and the v0.6.0 collector helpers.

Synthetic collector outputs are written in exactly the format of
run_v060_qualification.py (run-log.json plus raw/<name>.stdout), with probe
records shaped like the real `release-cells`, `memory-peak` and
`contention-probe` output (field names copied from those sources). No expected
verdict is encoded in the analysis itself.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analyze_v060_qualification as an  # noqa: E402
import run_v060_qualification as col  # noqa: E402

MATRIX = json.loads(an.MATRIX.read_text())
REF, CAND = "51e3b4da2de802a4ebf352b1e8a8311657e48d38", "c" * 40


def build(rev, dirty=False):
    return {"kind": "build", "knotrel_rev": rev, "knotrel_dirty": dirty, "probe": "x", "probes_dirty": False}


class Collector:
    """Writes a synthetic collector directory."""

    def __init__(self, root, pilot=False):
        self.root = Path(root)
        (self.root / "raw").mkdir(parents=True)
        self.children = []
        self.pilot = pilot

    def child(self, label, records, exit_code=0):
        name = f"{len(self.children) + 1:05d}-{label}"
        (self.root / "raw" / f"{name}.stdout").write_text("\n".join(json.dumps(r) for r in records) + "\n")
        self.children.append({"name": name, "argv": [], "exit": exit_code, "seconds": 0.1, "host": {}})

    def finish(self, stopped=None):
        log = {"meta": {"pilot": self.pilot}, "children": self.children, "started": "t"}
        if stopped:
            log["stopped"] = stopped
        else:
            log["finished"] = "t"
        (self.root / "run-log.json").write_text(json.dumps(log))


def r_record(cell, value):
    record = {"kind": cell["command"], "observation_ns": value}
    if cell["command"] == "churn":
        record.update({"slowest_op_ns": value // 10, "compactions": 1, "operations": 1000, "nodes": 100000})
    else:
        record["counts"] = [1, 2, 3, 4, 5]
    return record


def write_r(root, ratio_for, pairs=12, warmup=2, ref_rev=REF, cand_rev=CAND):
    out = Collector(root)
    for cell in MATRIX["experiments"]["R"]["cells"]:
        for index in range(warmup + pairs):
            phase = "warmup" if index < warmup else "analyzed"
            base = 1_000_000 + 1000 * index
            for arm, value in (("ref", base), ("cand", int(base * ratio_for(cell["id"], index)))):
                out.child(f"{cell['id']}-{phase}-{index:02d}-{arm}",
                          [build(ref_rev if arm == "ref" else cand_rev), r_record(cell, value)])
    out.finish()


class RAnalysis(unittest.TestCase):
    def test_classifies_improvement_pass_and_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            def ratio(cell_id, index):
                if "core-import" in cell_id:
                    return 0.5 + 0.001 * index  # clearly faster
                if "http-import" in cell_id:
                    return 1.5  # clearly slower than 10%
                return 1.0 + (0.01 if index % 2 else -0.01)
            write_r(tmp, ratio)
            result = an.analyze_r(Path(tmp), MATRIX, REF, CAND)
        self.assertEqual(result["R-core-import-sparse-100k-20-10"]["verdict"], "PASS (IMPROVED)")
        self.assertEqual(result["R-http-import-sparse-100k-20-10"]["verdict"], "REGRESSION")
        self.assertEqual(result["R-churn-same-sparse-100k"]["verdict"], "PASS")
        self.assertEqual(result["R-churn-fresh-sparse-100k"]["compactions"], {"ref": 1, "cand": 1})

    def test_rejects_wrong_identity_dirty_build_and_missing_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_r(tmp, lambda *_: 1.0, cand_rev="d" * 40)
            with self.assertRaisesRegex(an.AnalysisError, "expected c"):
                an.analyze_r(Path(tmp), MATRIX, REF, CAND)
        with tempfile.TemporaryDirectory() as tmp:
            write_r(tmp, lambda *_: 1.0, pairs=11)
            with self.assertRaisesRegex(an.AnalysisError, "11 complete pairs"):
                an.analyze_r(Path(tmp), MATRIX, REF, CAND)

    def test_rejects_stopped_failed_and_pilot_runs(self):
        for kind in ("stopped", "failed", "pilot"):
            with tempfile.TemporaryDirectory() as tmp:
                out = Collector(tmp, pilot=(kind == "pilot"))
                out.child("x-analyzed-00-ref", [build(REF)], exit_code=1 if kind == "failed" else 0)
                out.finish(stopped="x" if kind == "stopped" else None)
                with self.assertRaises(an.AnalysisError):
                    an.analyze_r(Path(tmp), MATRIX, REF, CAND)

    def test_rejects_arms_doing_different_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_r(tmp, lambda *_: 1.0)
            raw = Path(tmp) / "raw"
            victim = sorted(raw.glob("*R-core-import-sparse-10k-20-10-analyzed-05-cand.stdout"))[0]
            lines = [json.loads(line) for line in victim.read_text().splitlines()]
            lines[1]["counts"] = [9, 9, 9, 9, 9]
            victim.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
            with self.assertRaisesRegex(an.AnalysisError, "counts differ"):
                an.analyze_r(Path(tmp), MATRIX, REF, CAND)


def churn_records(rev, nets, peak):
    records = [build(rev), {"kind": "baseline", "live_heap_bytes": 1000, "peak_heap_bytes": 1000}]
    for cycle, net in enumerate(nets):
        records.append({"kind": "checkpoint", "cycle": cycle, "logical": [1], "expected": [1],
                        "net_live_heap_bytes": net, "peak_heap_bytes": 1000 + peak,
                        "engine_vertices": 10, "compacted_in_cycle": cycle == 2})
    return records


class RmemAnalysis(unittest.TestCase):
    def test_memory_tolerance_and_churn_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Collector(tmp)
            for cell in MATRIX["experiments"]["Rmem"]["cells"]:
                for arm, rev in (("ref", REF), ("cand", CAND)):
                    if cell["args"][0] == "churn":
                        nets = [100, 200, 150] if arm == "ref" else [100, 230, 150]
                        out.child(f"{cell['id']}-{arm}", churn_records(rev, nets, 300))
                    else:
                        big = 100 if arm == "ref" else 130
                        out.child(f"{cell['id']}-{arm}", [build(rev), {"kind": cell["args"][0], "peak_after": big,
                                                                        "live_after": 50, "transient_over_final": big - 50}])
            out.finish()
            result = an.analyze_rmem(Path(tmp), MATRIX, REF, CAND)
        self.assertEqual(result["Rmem-import-core-20-10"]["metrics"]["peak_after"]["verdict"], "REGRESSION")
        self.assertEqual(result["Rmem-import-core-20-10"]["metrics"]["live_after"]["verdict"], "PASS")
        churn = result["Rmem-churn-fresh-sparse"]["metrics"]["max_net_live"]
        self.assertEqual((churn["ref"], churn["cand"], churn["verdict"]), (200, 230, "PASS"))
        self.assertEqual(result["Rmem-churn-fresh-sparse"]["cand"]["compactions"], 1)

    def test_rejects_churn_count_mismatch(self):
        records = churn_records(REF, [1, 2], 3)
        records[2]["expected"] = [2]
        with self.assertRaisesRegex(an.AnalysisError, "logical counts"):
            an.churn_memory(records)


def config_record(config_id, mix, clients, rps, p99, lock_mean, latency_mean, statuses=None, errors=0):
    return {"kind": "config", "config": {"id": config_id, "mix": mix, "batch": 8, "clients": clients,
                                          "open_rate": None, "background": "none"},
            "requests_per_s": rps, "operations_per_s": rps * 8,
            "latency_ns": {"p50": p99 // 2, "p99": p99, "p999": p99, "max": p99, "mean": latency_mean},
            "statuses": statuses or {"200": 10}, "errors": errors,
            "fairness": {"jain": 1.0, "min_over_max": 1.0}, "outstanding_jobs": {"median": 4, "max": 4},
            "server_phases": {'knotrel_graph_lock_wait_seconds{kind="batch"}': {"mean_s": lock_mean, "count": 10},
                              'knotrel_graph_job_execution_seconds{kind="batch"}': {"mean_s": 1e-4, "count": 10},
                              'knotrel_graph_job_queue_seconds{kind="batch"}': {"mean_s": 1e-6, "count": 10}},
            "background": None, "server_rss_kib": 1000}


class MAnalysis(unittest.TestCase):
    def test_mdesc_rule_counts_saturated_read_configs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Collector(tmp)
            out.child("M-standalone-off-10k", [
                config_record("read95-b8-c16", "read95", 16, 1000, 2_000_000, 1.5e-3, 2_000_000),
                config_record("read95-b8-c4", "read95", 4, 1000, 2_000_000, 1.5e-3, 2_000_000),
                config_record("mixed50-b8-c16", "mixed50", 16, 1000, 2_000_000, 1.5e-3, 2_000_000),
                config_record("read95-b8-c64", "read95", 64, 1000, 2_000_000, 0.2e-3, 2_000_000),
            ])
            out.finish()
            result = an.analyze_mdesc(Path(tmp), MATRIX)
        self.assertEqual(result["m5_rule_i"]["evaluated"], 2)
        self.assertEqual(result["m5_rule_i"]["configs"], ["M-standalone-off-10k/read95-b8-c16"])
        self.assertAlmostEqual(result["rows"][0]["lock_share_of_latency"], 0.75)

    def write_mreg(self, tmp, cand_rps, cand_p99, statuses=None):
        out = Collector(tmp)
        for cell in MATRIX["experiments"]["M_reg"]["cells"]:
            for index in range(14):
                phase = "warmup" if index < 2 else "analyzed"
                jitter = 1 + 0.001 * index
                for arm in ("ref", "cand"):
                    rps = 1000 * jitter if arm == "ref" else cand_rps * jitter
                    p99 = int(1e6 * jitter) if arm == "ref" else int(cand_p99 * jitter)
                    out.child(f"{cell['id']}-{phase}-{index:02d}-{arm}",
                              [{"kind": "start"}, config_record(cell["id"], "read95", 16, rps, p99, 1e-3, 1e6,
                                                                statuses=statuses if arm == "cand" else None)])
        out.finish()

    def test_mreg_directions(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_mreg(tmp, cand_rps=800, cand_p99=1e6)  # 20% fewer requests/s
            result = an.analyze_mreg(Path(tmp), MATRIX)
        cell = next(iter(result.values()))
        self.assertEqual(cell["metrics"]["requests_per_s"]["status"], "REGRESSION")
        self.assertEqual(cell["metrics"]["latency_ns.p99"]["status"], "PASS")
        self.assertEqual(cell["verdict"], "REGRESSION")
        with tempfile.TemporaryDirectory() as tmp:
            self.write_mreg(tmp, cand_rps=1500, cand_p99=0.5e6)
            result = an.analyze_mreg(Path(tmp), MATRIX)
        cell = next(iter(result.values()))
        self.assertEqual(cell["metrics"]["requests_per_s"]["verdict"], "PASS (IMPROVED)")
        self.assertEqual(cell["metrics"]["latency_ns.p99"]["verdict"], "PASS (IMPROVED)")

    def test_mreg_rejects_error_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_mreg(tmp, cand_rps=1000, cand_p99=1e6, statuses={"200": 9, "503": 1})
            with self.assertRaisesRegex(an.AnalysisError, "503"):
                an.analyze_mreg(Path(tmp), MATRIX)


class CollectorHelpers(unittest.TestCase):
    def test_host_check(self):
        ok = {"batt": "Now drawing from 'AC Power'\n -InternalBattery-0", "therm": "Note: No thermal warning level has been recorded"}
        col.check_host(ok)
        with self.assertRaises(SystemExit):
            col.check_host({**ok, "batt": "Now drawing from 'Battery Power'"})
        with self.assertRaises(SystemExit):
            col.check_host({**ok, "therm": "CPU_Speed_Limit = 80\nthermal warning level is 2"})

    def test_balanced_orders(self):
        orders = col.balanced_orders(12, 3)
        self.assertEqual(sum(o == ["ref", "cand"] for o in orders), 6)
        self.assertEqual(orders, col.balanced_orders(12, 3))

    def test_last_json(self):
        stdout = '{"kind":"build"}\nnoise\n{"kind":"churn","observation_ns":5}\n'
        self.assertEqual(col.last_json(stdout, "churn")["observation_ns"], 5)
        with self.assertRaises(ValueError):
            col.last_json(stdout, "core-import")


if __name__ == "__main__":
    unittest.main()
