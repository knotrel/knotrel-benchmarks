//! Input generation, expected answers, statistics and JSON helpers of
//! `query-shape-probe` (v1.2.0 qualification, attempt 3, K3 and M1).
//!
//! Everything here is deterministic and independent of timing and of the
//! knotrel arm: the same arguments produce the same edge list, the same query
//! streams, the same expected answers and the same input fingerprint.
//! Vertex IDs are the vertex indices (`0..n` as `u64`).

use std::fmt::Write as _;

/// A seeded xorshift64 generator (the prototype's), seeded through splitmix64
/// so any seed, zero included, gives a non-zero state.
#[derive(Debug, Clone)]
pub struct Rng(u64);

/// One splitmix64 step: a well-mixed 64-bit value from `x`.
pub fn splitmix64(x: u64) -> u64 {
    let mut z = x.wrapping_add(0x9e37_79b9_7f4a_7c15);
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    z ^ (z >> 31)
}

impl Rng {
    /// A generator for `seed`.
    pub fn new(seed: u64) -> Self {
        let s = splitmix64(seed);
        Self(if s == 0 { 0x9e37_79b9_7f4a_7c15 } else { s })
    }

    /// The generator of query stream `stream` (a thread index) under `seed`.
    /// Stream generators never coincide with the graph generator (`Rng::new(seed)`).
    pub fn for_stream(seed: u64, stream: u64) -> Self {
        Self::new(splitmix64(seed ^ 0x5157_5350_0000_0000) ^ splitmix64(stream + 1))
    }

    /// Next raw value.
    pub fn next_u64(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }

    /// A value in `0..n` (`n > 0`; modulo bias is irrelevant here).
    pub fn below(&mut self, n: u64) -> u64 {
        self.next_u64() % n
    }
}

/// Union-find over `0..n` with path halving and union by size. It computes the
/// expected answers outside the timed region.
#[derive(Debug, Clone)]
pub struct UnionFind {
    parent: Vec<u32>,
    size: Vec<u32>,
}

impl UnionFind {
    /// `n` singletons.
    pub fn new(n: usize) -> Self {
        Self {
            parent: (0..n as u32).collect(),
            size: vec![1; n],
        }
    }

    /// The representative of `x`.
    pub fn find(&mut self, mut x: u32) -> u32 {
        while self.parent[x as usize] != x {
            let p = self.parent[x as usize];
            self.parent[x as usize] = self.parent[p as usize];
            x = self.parent[x as usize];
        }
        x
    }

    /// Joins the components of `a` and `b`.
    pub fn union(&mut self, a: u32, b: u32) {
        let (mut a, mut b) = (self.find(a), self.find(b));
        if a == b {
            return;
        }
        if self.size[a as usize] < self.size[b as usize] {
            std::mem::swap(&mut a, &mut b);
        }
        self.parent[b as usize] = a;
        self.size[a as usize] += self.size[b as usize];
    }

    /// Whether `a` and `b` are in one component.
    pub fn same(&mut self, a: u32, b: u32) -> bool {
        self.find(a) == self.find(b)
    }

    /// Size of the component of `x`.
    pub fn component_size(&mut self, x: u32) -> u32 {
        let r = self.find(x);
        self.size[r as usize]
    }

    /// The representative of a largest component (the smallest such root).
    pub fn largest_root(&mut self) -> u32 {
        let n = self.parent.len() as u32;
        let mut best = (0u32, u32::MAX);
        for x in 0..n {
            if self.parent[x as usize] == x {
                let s = self.size[x as usize];
                if s > best.0 {
                    best = (s, x);
                }
            }
        }
        best.1
    }
}

/// The five query shapes of plan section 14.5.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Shape {
    /// Random graph with 2n edges; random pairs inside the giant component.
    S1,
    /// Random giant component plus small components; small vertex → giant vertex.
    S2,
    /// Chain; its two ends.
    L1,
    /// Cycle; vertex `i` and `i + n/2`.
    L2,
    /// Chain without its middle edge; one end of each half.
    L3,
}

impl Shape {
    /// Parses `s1|s2|l1|l2|l3` (case-insensitive).
    pub fn parse(s: &str) -> Option<Self> {
        match s.to_ascii_lowercase().as_str() {
            "s1" => Some(Self::S1),
            "s2" => Some(Self::S2),
            "l1" => Some(Self::L1),
            "l2" => Some(Self::L2),
            "l3" => Some(Self::L3),
            _ => None,
        }
    }

    /// The lower-case name used on the command line and in the JSON.
    pub fn name(self) -> &'static str {
        match self {
            Self::S1 => "s1",
            Self::S2 => "s2",
            Self::L1 => "l1",
            Self::L2 => "l2",
            Self::L3 => "l3",
        }
    }

    /// The answer every query of this shape has by construction.
    pub fn expected_answer(self) -> bool {
        !matches!(self, Self::S2 | Self::L3)
    }

    /// Default timed queries per thread, calibrated on an Apple M3 (8 cores)
    /// against the slower arm, v1.1.0, at 16 threads (wall time per process,
    /// graph build included): S1 1,000 → about 3 s (v1.1.0 short queries
    /// search most of the giant, about 0.7 ms each); S2 10,000 → well under
    /// 1 s on both arms; L1/L2/L3 1,000 → about 1–1.3 s. Both arms of a pair
    /// must run the same count (it is part of the input fingerprint).
    pub fn default_queries(self) -> usize {
        match self {
            Self::S1 | Self::L1 | Self::L2 | Self::L3 => 1_000,
            Self::S2 => 10_000,
        }
    }
}

/// A generated input: the vertex count, the edge list in insertion order, and
/// a query sampler with its union-find.
#[derive(Debug, Clone)]
pub struct Instance {
    /// The shape.
    pub shape: Shape,
    /// Vertices `0..vertices`.
    pub vertices: u64,
    /// Edges in the order they are linked (may hold duplicates; no self loops).
    pub edges: Vec<(u64, u64)>,
    uf: UnionFind,
    /// For S1: vertices of the giant component; for S2: the giant side.
    giant: Vec<u64>,
    /// For S2: the vertices of the small components.
    small: Vec<u64>,
}

/// `count` random edges over `0..n` without self loops (n ≥ 2).
pub fn random_edges(rng: &mut Rng, n: u64, count: u64) -> Vec<(u64, u64)> {
    let mut edges = Vec::with_capacity(count as usize);
    while (edges.len() as u64) < count {
        let (a, b) = (rng.below(n), rng.below(n));
        if a != b {
            edges.push((a, b));
        }
    }
    edges
}

/// Edges of the chain `0 - 1 - … - (n-1)`.
pub fn chain_edges(n: u64) -> Vec<(u64, u64)> {
    (1..n).map(|i| (i - 1, i)).collect()
}

/// Vertex count of the small components of S2: 1 % of the vertices, at least 8.
pub fn s2_small_vertices(n: u64) -> u64 {
    (n / 100).max(8)
}

impl Instance {
    /// Generates `shape` on `vertices` vertices from `seed`.
    ///
    /// # Panics
    /// If `vertices` is too small for the shape (S1/S2 need ≥ 100, L* ≥ 4).
    pub fn generate(shape: Shape, vertices: u64, seed: u64) -> Self {
        let n = vertices;
        let mut rng = Rng::new(seed);
        let mut giant = Vec::new();
        let mut small = Vec::new();
        let edges = match shape {
            Shape::S1 => {
                assert!(n >= 100, "s1 needs at least 100 vertices");
                random_edges(&mut rng, n, 2 * n)
            }
            Shape::S2 => {
                assert!(n >= 100, "s2 needs at least 100 vertices");
                let small_n = s2_small_vertices(n);
                let g = n - small_n;
                let mut edges = random_edges(&mut rng, g, 2 * g);
                // Small components: paths of 2..=8 vertices over g..n; a
                // remainder of one vertex joins the previous component.
                let mut start = g;
                while start < n {
                    let mut len = 2 + rng.below(7);
                    if n - start < len || n - start - len == 1 {
                        len = n - start;
                    }
                    for v in start + 1..start + len {
                        edges.push((v - 1, v));
                    }
                    start += len;
                }
                small.extend(g..n);
                edges
            }
            Shape::L1 => {
                assert!(n >= 4, "l1 needs at least 4 vertices");
                chain_edges(n)
            }
            Shape::L2 => {
                assert!(n >= 4, "l2 needs at least 4 vertices");
                let mut e = chain_edges(n);
                e.push((n - 1, 0));
                e
            }
            Shape::L3 => {
                assert!(n >= 4, "l3 needs at least 4 vertices");
                (1..n).filter(|&i| i != n / 2).map(|i| (i - 1, i)).collect()
            }
        };
        let mut uf = UnionFind::new(n as usize);
        for &(a, b) in &edges {
            uf.union(a as u32, b as u32);
        }
        if matches!(shape, Shape::S1 | Shape::S2) {
            let root = uf.largest_root();
            giant = (0..n).filter(|&v| uf.find(v as u32) == root).collect();
        }
        Self {
            shape,
            vertices: n,
            edges,
            uf,
            giant,
            small,
        }
    }

    /// Vertices of the giant component (S1, S2; empty otherwise).
    pub fn giant(&self) -> &[u64] {
        &self.giant
    }

    /// Vertices of the small components (S2; empty otherwise).
    pub fn small(&self) -> &[u64] {
        &self.small
    }

    /// The next query of a stream.
    pub fn sample(&self, rng: &mut Rng) -> (u64, u64) {
        let n = self.vertices;
        let pick = |rng: &mut Rng, v: &[u64]| v[rng.below(v.len() as u64) as usize];
        let flip = |rng: &mut Rng, a: u64, b: u64| {
            if rng.next_u64() & 1 == 0 {
                (a, b)
            } else {
                (b, a)
            }
        };
        match self.shape {
            Shape::S1 => (pick(rng, &self.giant), pick(rng, &self.giant)),
            Shape::S2 => (pick(rng, &self.small), pick(rng, &self.giant)),
            Shape::L1 | Shape::L3 => flip(rng, 0, n - 1),
            Shape::L2 => {
                let i = rng.below(n);
                (i, (i + n / 2) % n)
            }
        }
    }

    /// `count` queries of stream `stream` under `seed`, each with its answer
    /// from the union-find.
    pub fn queries(&mut self, seed: u64, stream: u64, count: usize) -> Vec<Query> {
        let mut rng = Rng::for_stream(seed, stream);
        (0..count)
            .map(|_| {
                let (a, b) = self.sample(&mut rng);
                Query {
                    a,
                    b,
                    expected: self.expected(a, b),
                }
            })
            .collect()
    }

    /// The expected answer for `(a, b)` from the union-find.
    pub fn expected(&mut self, a: u64, b: u64) -> bool {
        self.uf.same(a as u32, b as u32)
    }

    /// Size of the component of `v`.
    pub fn component_size(&mut self, v: u64) -> u32 {
        self.uf.component_size(v as u32)
    }
}

/// One query with its expected answer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Query {
    /// Source vertex.
    pub a: u64,
    /// Target vertex.
    pub b: u64,
    /// Expected `connected(a, b)`.
    pub expected: bool,
}

/// FNV-1a 64 over a stream of little-endian `u64` words and tags.
#[derive(Debug, Clone)]
pub struct Fnv1a64(u64);

impl Default for Fnv1a64 {
    fn default() -> Self {
        Self(0xcbf2_9ce4_8422_2325)
    }
}

impl Fnv1a64 {
    /// Feeds bytes.
    pub fn bytes(&mut self, bytes: &[u8]) {
        for &b in bytes {
            self.0 ^= u64::from(b);
            self.0 = self.0.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }

    /// Feeds one `u64`, little-endian.
    pub fn word(&mut self, w: u64) {
        self.bytes(&w.to_le_bytes());
    }

    /// Feeds a vertex count and an edge list.
    pub fn graph(&mut self, vertices: u64, edges: &[(u64, u64)]) {
        self.bytes(b"graph");
        self.word(vertices);
        self.word(edges.len() as u64);
        for &(a, b) in edges {
            self.word(a);
            self.word(b);
        }
    }

    /// Feeds one stream's queries (endpoints only).
    pub fn queries(&mut self, stream: u64, queries: &[Query]) {
        self.bytes(b"stream");
        self.word(stream);
        self.word(queries.len() as u64);
        for q in queries {
            self.word(q.a);
            self.word(q.b);
        }
    }

    /// The digest.
    pub fn finish(&self) -> u64 {
        self.0
    }

    /// The digest as `0x` + 16 lower-case hex digits.
    pub fn hex(&self) -> String {
        format!("0x{:016x}", self.0)
    }
}

/// Nearest-rank percentile `num/den` of a sorted, non-empty slice: the value
/// at rank `ceil(num/den · len)` (1-based, at least 1).
///
/// # Panics
/// If `sorted` is empty or `num > den`.
pub fn nearest_rank(sorted: &[u64], num: u64, den: u64) -> u64 {
    assert!(!sorted.is_empty() && num <= den && den > 0);
    let len = sorted.len() as u64;
    let rank = (num * len).div_ceil(den).max(1);
    sorted[(rank - 1) as usize]
}

/// Nearest-rank percentile of signed values (sorted, non-empty).
pub fn nearest_rank_i64(sorted: &[i64], num: u64, den: u64) -> i64 {
    assert!(!sorted.is_empty() && num <= den && den > 0);
    let len = sorted.len() as u64;
    let rank = (num * len).div_ceil(den).max(1);
    sorted[(rank - 1) as usize]
}

/// A hand-written JSON object (no serde): keys in insertion order.
#[derive(Debug, Default)]
pub struct JsonObject {
    out: String,
}

/// Escapes a string as a JSON string literal.
pub fn json_string(s: &str) -> String {
    let mut o = String::with_capacity(s.len() + 2);
    o.push('"');
    for c in s.chars() {
        match c {
            '"' => o.push_str("\\\""),
            '\\' => o.push_str("\\\\"),
            '\n' => o.push_str("\\n"),
            '\r' => o.push_str("\\r"),
            '\t' => o.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                let _ = write!(o, "\\u{:04x}", c as u32);
            }
            c => o.push(c),
        }
    }
    o.push('"');
    o
}

/// Formats a float for JSON (finite; non-finite values become `null`).
pub fn json_f64(x: f64) -> String {
    if x.is_finite() {
        let s = format!("{x:.6}");
        let s = s.trim_end_matches('0').trim_end_matches('.');
        if s.is_empty() || s == "-" {
            "0".into()
        } else {
            s.into()
        }
    } else {
        "null".into()
    }
}

impl JsonObject {
    /// An empty object.
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds a pre-rendered JSON value.
    pub fn raw(mut self, key: &str, value: impl AsRef<str>) -> Self {
        if !self.out.is_empty() {
            self.out.push(',');
        }
        self.out.push_str(&json_string(key));
        self.out.push(':');
        self.out.push_str(value.as_ref());
        self
    }

    /// Adds a string.
    pub fn str(self, key: &str, value: &str) -> Self {
        let v = json_string(value);
        self.raw(key, v)
    }

    /// Adds an integer (or anything whose `Display` is a JSON number).
    pub fn num(self, key: &str, value: impl std::fmt::Display) -> Self {
        let v = value.to_string();
        self.raw(key, v)
    }

    /// Adds a float.
    pub fn float(self, key: &str, value: f64) -> Self {
        let v = json_f64(value);
        self.raw(key, v)
    }

    /// Adds a nested object.
    pub fn obj(self, key: &str, value: JsonObject) -> Self {
        let v = value.finish();
        self.raw(key, v)
    }

    /// The rendered object.
    pub fn finish(self) -> String {
        format!("{{{}}}", self.out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rng_is_deterministic_and_streams_differ() {
        let a: Vec<u64> = (0..5)
            .scan(Rng::new(42), |r, _| Some(r.next_u64()))
            .collect();
        let b: Vec<u64> = (0..5)
            .scan(Rng::new(42), |r, _| Some(r.next_u64()))
            .collect();
        assert_eq!(a, b);
        let mut z = Rng::new(0);
        assert_ne!(z.next_u64(), 0);
        let s0 = Rng::for_stream(42, 0).next_u64();
        let s1 = Rng::for_stream(42, 1).next_u64();
        assert_ne!(s0, s1);
        assert_ne!(s0, Rng::new(42).next_u64());
    }

    #[test]
    fn union_find_basics() {
        let mut uf = UnionFind::new(6);
        uf.union(0, 1);
        uf.union(1, 2);
        uf.union(4, 5);
        assert!(uf.same(0, 2));
        assert!(!uf.same(2, 3));
        assert_eq!(uf.component_size(1), 3);
        let r = uf.largest_root();
        assert!(uf.same(r, 0));
    }

    #[test]
    fn nearest_rank_percentiles() {
        let v: Vec<u64> = (1..=100).collect();
        assert_eq!(nearest_rank(&v, 50, 100), 50);
        assert_eq!(nearest_rank(&v, 99, 100), 99);
        assert_eq!(nearest_rank(&v, 100, 100), 100);
        assert_eq!(nearest_rank(&v, 0, 100), 1);
        assert_eq!(nearest_rank(&[7], 99, 100), 7);
        let w = [1, 2, 3, 4];
        assert_eq!(nearest_rank(&w, 1, 2), 2);
        assert_eq!(nearest_rank(&[1, 2, 3], 1, 2), 2);
        assert_eq!(nearest_rank(&w, 99, 100), 4);
        assert_eq!(nearest_rank_i64(&[-3, 0, 5], 1, 2), 0);
    }

    #[test]
    fn s1_queries_are_connected_in_the_giant() {
        let mut inst = Instance::generate(Shape::S1, 2_000, 42);
        assert_eq!(inst.edges.len(), 4_000);
        assert!(
            inst.edges
                .iter()
                .all(|&(a, b)| a != b && a < 2_000 && b < 2_000)
        );
        // Average degree 4: the giant holds most vertices.
        assert!(inst.giant().len() > 1_800, "{}", inst.giant().len());
        let qs = inst.queries(42, 0, 500);
        assert!(qs.iter().all(|q| q.expected));
    }

    #[test]
    fn s2_queries_are_disconnected_and_small_components_are_small() {
        let n = 10_000;
        let mut inst = Instance::generate(Shape::S2, n, 7);
        let small = inst.small().to_vec();
        assert_eq!(small.len() as u64, s2_small_vertices(n));
        for &v in &small {
            let s = inst.component_size(v);
            assert!((2..=9).contains(&s), "vertex {v} in component of {s}");
        }
        let qs = inst.queries(7, 3, 1_000);
        assert!(qs.iter().all(|q| !q.expected));
        assert!(qs.iter().all(|q| q.a >= n - small.len() as u64));
    }

    #[test]
    fn long_shapes_have_the_expected_answers() {
        let n = 1_000;
        for (shape, edges) in [(Shape::L1, n - 1), (Shape::L2, n), (Shape::L3, n - 2)] {
            let mut inst = Instance::generate(shape, n, 1);
            assert_eq!(inst.edges.len() as u64, edges, "{shape:?}");
            let qs = inst.queries(1, 0, 50);
            for q in &qs {
                assert_eq!(q.expected, shape.expected_answer(), "{shape:?} {q:?}");
                match shape {
                    Shape::L2 => assert_eq!((q.a + n / 2) % n, q.b),
                    _ => assert_eq!(q.a.min(q.b) + q.a.max(q.b), n - 1),
                }
            }
        }
        // The L3 halves are each connected.
        let mut l3 = Instance::generate(Shape::L3, n, 1);
        assert!(l3.expected(0, n / 2 - 1));
        assert!(l3.expected(n / 2, n - 1));
        assert!(!l3.expected(n / 2 - 1, n / 2));
    }

    #[test]
    fn fingerprint_is_stable_and_input_sensitive() {
        let fp = |shape, seed, stream| {
            let mut inst = Instance::generate(shape, 1_000, seed);
            let qs = inst.queries(seed, stream, 100);
            let mut h = Fnv1a64::default();
            h.graph(inst.vertices, &inst.edges);
            h.queries(stream, &qs);
            h.finish()
        };
        assert_eq!(fp(Shape::S1, 42, 0), fp(Shape::S1, 42, 0));
        assert_ne!(fp(Shape::S1, 42, 0), fp(Shape::S1, 43, 0));
        assert_ne!(fp(Shape::S1, 42, 0), fp(Shape::S1, 42, 1));
        assert_ne!(fp(Shape::L1, 42, 0), fp(Shape::L3, 42, 0));
        // Known FNV-1a 64 vectors.
        let mut h = Fnv1a64::default();
        assert_eq!(h.finish(), 0xcbf2_9ce4_8422_2325);
        h.bytes(b"a");
        assert_eq!(h.finish(), 0xaf63_dc4c_8601_ec8c);
        assert_eq!(h.hex(), "0xaf63dc4c8601ec8c");
    }

    #[test]
    fn generation_is_pinned() {
        // Pins the generators and the stream seeding: a change here changes
        // every fingerprint of a frozen campaign, so it must be deliberate.
        let pinned = |shape, stream| {
            let mut inst = Instance::generate(shape, 1_000, 42);
            let qs = inst.queries(42, stream, 100);
            let mut h = Fnv1a64::default();
            h.graph(inst.vertices, &inst.edges);
            h.queries(stream, &qs);
            h.hex()
        };
        let got: Vec<String> = [Shape::S1, Shape::S2, Shape::L1, Shape::L2, Shape::L3]
            .into_iter()
            .map(|s| pinned(s, 3))
            .collect();
        let want = [
            "0x9553dc3d216cac10",
            "0x9e7372ef8cbaf93b",
            "0xf536e8f7c84f0b7d",
            "0xf394b99aaad927ec",
            "0xcab680e0acbbcc7f",
        ];
        assert_eq!(got, want, "{got:?}");
    }

    #[test]
    fn json_rendering() {
        let o = JsonObject::new()
            .str("tool", "q\"s")
            .num("n", 3)
            .float("f", 1.5)
            .float("z", 0.0)
            .obj("o", JsonObject::new().num("p50", 7));
        assert_eq!(
            o.finish(),
            r#"{"tool":"q\"s","n":3,"f":1.5,"z":0,"o":{"p50":7}}"#
        );
        assert_eq!(json_f64(f64::NAN), "null");
        assert_eq!(json_f64(2.0), "2");
    }
}
