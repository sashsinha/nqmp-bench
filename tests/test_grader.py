from nqmp_bench.grader import is_correct


def test_boolean_norm():
  assert is_correct('boolean', 'YES', 'Yes')
  assert is_correct('boolean', 'no', 'No')


def test_id_list_norm():
  assert is_correct('id_list', 'A,B', 'A, B')
  assert not is_correct('id_list', 'A,B', 'A,B,C')
