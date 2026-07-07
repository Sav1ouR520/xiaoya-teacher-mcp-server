# Rich Question Text (`title_md` / `title_raw`)

When AI produces Markdown, pass it through Markdown fields such as `title_md`, `text_md`, `option_text_md`, or `answer_md`. The MCP server converts the supported Markdown subset to XiaoYa Draft.js raw content automatically.

Supported Markdown in automatic conversion:

- `#` through `######` headings
- ordered and unordered list items
- blockquotes
- fenced code blocks
- inline `**bold**`, `*italic*`, `` `code` ``, and `<u>underline</u>`
- image placeholders such as `![节点图](asset://img_1)`, paired with `title_assets` / `text_assets` / `answer_assets`
- attachment placeholders such as `[实验附件](asset://file_1)`, paired with `title_assets` / `text_assets` / `answer_assets`

Asset example:

```json
{
  "title_md": "题目文字\n\n![节点图](asset://img_1)\n\n[实验附件](asset://file_1)",
  "title_assets": [
    {"id": "img_1", "type": "image", "name": "节点图.png", "file_path": "/abs/node.png"},
    {"id": "file_1", "type": "attachment", "name": "实验附件.zip", "file_path": "/abs/lab.zip"}
  ]
}
```

Use `parse_mode="markdown"` when reading papers or answers if the next step is AI editing. The response returns standard Markdown fields plus assets lists, for example `title_md` and `title_assets`.

Use raw Draft.js fields such as `title_raw` only when exact block/entity control is required.

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

Images and disk attachments are supported through the Markdown asset workflow above. Tables, formulas, and videos still require dedicated editor support; keep them as Markdown/code text unless a dedicated helper exists. Broken Draft.js entity references may create a question that saves but renders incorrectly.
