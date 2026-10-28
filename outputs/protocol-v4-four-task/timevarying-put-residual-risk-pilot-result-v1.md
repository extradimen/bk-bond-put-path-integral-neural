# T-E/T-B C and D residual derivative pilot result

The frozen 40 fit-group rows (T-E/T-B × C/D × five seeds × groups 0–1) completed. Run `20261023T222545Z__1627c004__timevarying-put-residual-risk-pilot-v1` on `campus-3090-2` has node OS child wait code 0 and checksum-verified return. Inputs and immutable snapshot are recorded in the stage receipts; row-level results are in `outputs/timevarying-put-residual-risk-pilot-v1/results/pilot.jsonl`.

| Cell | Method | Mean absolute price error | Mean absolute seven-coordinate derivative error | Maximum absolute derivative error |
| --- | --- | ---: | ---: | ---: |
| T-E | C | 3.50e-6 | 1.11e-5 | 1.19e-4 |
| T-E | D | 5.00e-6 | 1.81e-5 | 1.67e-4 |
| T-B | C | 6.91e-6 | 2.02e-5 | 2.01e-4 |
| T-B | D | 6.35e-6 | 1.75e-5 | 1.45e-4 |

These are exploratory results from two test groups per cell. Each C/D derivative combines the analytic residual-network input gradient with the frozen A/Dbase central-difference gradient. Baseline numerical resolution sensitivity is inherited by the residual method, so the four-group values do not certify full A/C/D risk quality or imply a method-family ranking. A larger, separately frozen audit remains necessary.
