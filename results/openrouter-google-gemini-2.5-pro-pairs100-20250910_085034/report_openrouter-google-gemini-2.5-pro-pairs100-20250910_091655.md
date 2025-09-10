# NQMP Benchmark Report

**Client/Model:** openrouter / google/gemini-2.5-pro  
**Pairs / Seed:** 100 / 42  
**Timestamp:** 20250910_091655

**Item Accuracy:** 0.990  
**Pair Joint Accuracy:** 0.980

## Accuracy by Operator

| operator                  |   item_accuracy |
|:--------------------------|----------------:|
| and/or                    |        1        |
| any/all                   |        1        |
| any/all_subset            |        1        |
| atleast/atmost            |        1        |
| demorgan_and/or           |        1        |
| even/odd                  |        1        |
| exactly/atleast           |        1        |
| exactly1/atleast1         |        1        |
| majority/half             |        1        |
| more/atleast_as_many      |        1        |
| negation                  |        1        |
| none/notall               |        1        |
| range_inclusive/exclusive |        1        |
| unless/or                 |        0.833333 |
| xor/or                    |        1        |

![Operator Accuracy](operator_accuracy_openrouter-google-gemini-2.5-pro-pairs100-20250910_091655.png)
