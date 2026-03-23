# Runbook: Run Course

## Typical Command

```powershell
python -m processagent.cli run-course `
  --book-title "数据库系统概论" `
  --input-dir .\captions `
  --output-dir .\out `
  --toc-file .\toc.txt `
  --backend openai_compatible
```

## Resume

- 默认 `resume`
- 仅当显式传 `--clean` 时清理该课程 runtime

## Status

```powershell
python -m processagent.cli show-status `
  --book-title "数据库系统概论" `
  --input-dir .\captions `
  --output-dir .\out
```
