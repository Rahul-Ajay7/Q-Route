# Historical evidence

These archives preserve old numerical evidence without scattering duplicate
outputs through the active project. Every file was checked byte-for-byte by
SHA-256 before its loose original was removed.

| Archive | Contents |
|---|---|
| [v1-comparisons.zip](v1-comparisons.zip) | Full v1 supplied-case suite, Solomon checks, early pilot, manifests, raw data and original source snapshots |
| [development.zip](development.zip) | V2 development cases/seeds, all ablations, raw outcomes and source snapshots |
| [member-artifacts.zip](member-artifacts.zip) | Original member-generated outputs, historical plots/reports, old patch tools and logs |

[INDEX.json](INDEX.json) records archive hashes and sizes. Each ZIP contains an
`ARCHIVE_INDEX.json` with the original project-relative path, byte size and
SHA-256 of every stored file. Negative and mixed outcomes were preserved.

To restore old evidence under a temporary project folder, from the project root:

```powershell
Expand-Archive -LiteralPath results/archive/v1-comparisons.zip -DestinationPath results/restored
venv\Scripts\python.exe -B -m team_benchmark.verify_results results/restored/results/comparison/full_suite
```

Archive entries retain their original project-relative paths. Historical
manifests are not rewritten; the verifier resolves old input paths through
`docs/PATH_MIGRATION.json` and checks original source snapshots. No archived
source is executed by the verifier.

For current results, use [v2 validation](../comparison/hybrid_v2_validation/REPORT.md).
