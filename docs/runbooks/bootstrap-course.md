# Runbook: Bootstrap Course

## Typical Command

```powershell
python -m processagent.cli build-blueprint `
  --book-title "数据库系统概论" `
  --input-dir .\captions `
  --output-dir .\out `
  --toc-file .\toc.txt
```

## Notes

- 有 TOC 时优先 deterministic 生成 blueprint
- 无 TOC 时，若配置了远程 backend，则允许 `blueprint_builder` 补结构
- 产物会写到 `out/courses/<course_id>/course_blueprint.json`
