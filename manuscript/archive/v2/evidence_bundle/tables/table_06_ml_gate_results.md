# Preview: table_06_ml_gate_results

Generated from the adjacent CSV for human inspection. The CSV is canonical.

| gate | result | units | effect_on_downstream | selection_regret_executed | source_path | audit_status |
| --- | --- | --- | --- | --- | --- | --- |
| effect_prediction | fail | boolean | required prerequisite | False | outputs/phase97_v0.9.7/gate_evidence.json | computed from artifacts |
| empirical_location_leakage | pass | boolean | required prerequisite | False | outputs/phase97_v0.9.7/gate_evidence.json | computed from artifacts |
| independent_empirical_effect_validation | fail | boolean | required prerequisite | False | outputs/phase97_v0.9.7/gate_evidence.json | computed from artifacts |
| ood_performance | fail | boolean | required prerequisite | False | outputs/phase97_v0.9.7/gate_evidence.json | computed from artifacts |
| target_specific_uncertainty | pass | boolean | required prerequisite | False | outputs/phase97_v0.9.7/gate_evidence.json | computed from artifacts |
| downstream_execution | blocked | decision | blocked; selection/oracle/regret must not run | False | outputs/phase97_v0.9.7/gate_evidence.json | negative finding preserved |
