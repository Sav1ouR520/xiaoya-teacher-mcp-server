# Rich Question Text (`title_raw`)

XiaoYa question text uses Draft.js raw content:

```json
{
  "blocks": [
    {
      "text": "一行文本",
      "type": "unstyled",
      "inlineStyleRanges": [{"offset": 0, "length": 4, "style": "BOLD"}],
      "entityRanges": []
    }
  ],
  "entityMap": {}
}
```

Each visual line is one block. Empty lines are `{"text": "", "type": "unstyled"}` blocks. Offsets and lengths use UTF-16 code units; Chinese characters count as one unit.

## Stable Block Types

| Type | Use |
|---|---|
| `unstyled` | Normal text, default |
| `header-one` to `header-six` | Section headings |
| `ordered-list-item` | Numbered lists |
| `unordered-list-item` | Bullet lists |
| `code-block` | Code, sample input/output |
| `blockquote` | Quoted material or prompts |
| `atomic` | Entity-backed media blocks |

Prefer `unstyled`, heading blocks, lists, and `code-block` for MCP-created question text.

## Inline Styles

Common styles:

- `BOLD`, `ITALIC`, `UNDERLINE`, `CODE`
- `lineThrough`, `SUBSCRIPT`, `SUPERSCRIPT`
- `fontSize-12` through `fontSize-60` for supported size steps
- `fontFamily-msYaHei`, `song`, `fangSong`, `kaiTi`, `arial`, `timesNewRoman`, `courierNew`, `tahoma`, `verdana`, `sans-serif`
- `color-#hex` and `backgroundColor-#hex` for platform palette colors
- Semantic color styles such as `color-red`, `color-blue`, `backgroundColor-yellow`

Use styling sparingly. Plain blocks with bold section labels are the most robust.

## Minimal Template

```json
{
  "blocks": [
    {"text": "【题目描述】", "type": "unstyled", "inlineStyleRanges": [{"offset": 0, "length": 6, "style": "BOLD"}], "entityRanges": []},
    {"text": "题目正文。", "type": "unstyled", "inlineStyleRanges": [], "entityRanges": []},
    {"text": "", "type": "unstyled", "inlineStyleRanges": [], "entityRanges": []},
    {"text": "【输入格式】", "type": "unstyled", "inlineStyleRanges": [{"offset": 0, "length": 6, "style": "BOLD"}], "entityRanges": []},
    {"text": "输入说明。", "type": "unstyled", "inlineStyleRanges": [], "entityRanges": []},
    {"text": "", "type": "unstyled", "inlineStyleRanges": [], "entityRanges": []},
    {"text": "【样例输入】", "type": "unstyled", "inlineStyleRanges": [{"offset": 0, "length": 6, "style": "BOLD"}], "entityRanges": []},
    {"text": "3", "type": "code-block", "inlineStyleRanges": [], "entityRanges": []},
    {"text": "1 2 3", "type": "code-block", "inlineStyleRanges": [], "entityRanges": []}
  ],
  "entityMap": {}
}
```

## Entity Caution

Images, links, formulas, tables, and videos require coordinated `entityRanges` and `entityMap` data. Unless a dedicated helper exists, prefer asking the teacher to add those rich media elements in the XiaoYa web editor. Broken entity references may create a question that saves but renders incorrectly.
