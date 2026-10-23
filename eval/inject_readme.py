"""Copy results/results_table.md into README.md between the RESULTS markers, so README numbers always
come from the eval outputs. Run after eval/report.py."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
readme = (ROOT / "README.md").read_text()
table = (ROOT / "results" / "results_table.md").read_text()
start, end = "<!-- RESULTS -->", "<!-- /RESULTS -->"
block = f"{start}\n{table}\n![errors caught per type](results/chart_recall_test.png)\n\n![extraction by model](results/chart_models_test.png)\n{end}"
if end in readme:
    before = readme.split(start)[0]
    after = readme.split(end)[1]
    readme = before + block + after
else:
    readme = readme.replace(start, block)
(ROOT / "README.md").write_text(readme)
print("README results block updated")
