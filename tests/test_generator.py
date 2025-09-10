from nqmp_bench.generator import generate_pairs, GenConfig


def test_generate_pairs_count():
  pairs = generate_pairs(GenConfig(seed=1, num_pairs=7))
  assert len(pairs) == 7
  # ensure deterministic
  pairs2 = generate_pairs(GenConfig(seed=1, num_pairs=7))
  assert [p.id for p in pairs] == [p.id for p in pairs2]
