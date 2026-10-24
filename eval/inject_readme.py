"""Copy results/results_table.md into docs/evaluation.md between the RESULTS markers, so the numbers in the docs
always come from the eval outputs. Run after eval/report.py. (The README keeps only the headline numbers.)"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
target = ROOT / "docs" / "evaluation.md"
readme = target.read_text()
table = (ROOT / "results" / "results_table.md").read_text()
start, end = "<!-- RESULTS -->", "<!-- /RESULTS -->"
block = f"{start}\n{table}\n![errors caught per type](../results/chart_recall_test.png)\n\n![extraction by model](../results/chart_models_test.png)\n{end}"
if end in readme:
    before = readme.split(start)[0]
    after = readme.split(end)[1]
    readme = before + block + after
else:
    readme = readme.replace(start, block)
target.write_text(readme)
print("docs/evaluation.md results block updated")
