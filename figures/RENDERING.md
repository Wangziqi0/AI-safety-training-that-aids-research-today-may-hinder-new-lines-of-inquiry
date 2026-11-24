# Reproduce the heading and data for main Figure 5

The numerical table for main Figure 5 is the outer review archive's Figure 3 source and the innermost archive's Figure 2 source. The three CSV files are byte-identical.

1. Extract `Data_and_code.zip` into a clean directory. Extract its `previous/Data_and_code.zip` into a second directory. Within that second directory, extract `previous/Data_and_code.zip` into a third directory.
2. In a working copy of the third directory’s `figures/make_figures.py`, locate the function `figures_two`. Change its panel d heading from `Forecasting a 1.5B weight displacement` to `Forecasting 1.5B outcome shifts`. The input to the calculation is the given weight displacement. The forecast concerns the directions of outcome changes.
3. From that third directory, run `python3 figures/make_figures.py --figure 2 --data figures --out rebuilt` in the analysis environment documented in the archive (NumPy, Matplotlib and DejaVu Sans). The file `rebuilt/fig2.pdf` corresponds to main Figure 5. The generator also writes SVG and PNG. File metadata and font rendering may vary by environment.
