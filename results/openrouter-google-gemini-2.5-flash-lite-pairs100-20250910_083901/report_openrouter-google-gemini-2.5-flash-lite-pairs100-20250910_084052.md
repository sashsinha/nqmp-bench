# NQMP Benchmark Report

**Client/Model:** openrouter / google/gemini-2.5-flash-lite  
**Pairs / Seed:** 100 / 42  
**Timestamp:** 20250910_084052

**Item Accuracy:** 0.760  
**Pair Joint Accuracy:** 0.620

## Accuracy by Operator

| operator                  |   item_accuracy |
|:--------------------------|----------------:|
| and/or                    |        0.5      |
| any/all                   |        1        |
| any/all_subset            |        1        |
| atleast/atmost            |        0.785714 |
| demorgan_and/or           |        0.416667 |
| even/odd                  |        0.583333 |
| exactly/atleast           |        0.6875   |
| exactly1/atleast1         |        0.888889 |
| majority/half             |        1        |
| more/atleast_as_many      |        0.857143 |
| negation                  |        1        |
| none/notall               |        1        |
| range_inclusive/exclusive |        0.9      |
| unless/or                 |        0.333333 |
| xor/or                    |        0.125    |

![Operator Accuracy](operator_accuracy_openrouter-google-gemini-2.5-flash-lite-pairs100-20250910_084052.png)
