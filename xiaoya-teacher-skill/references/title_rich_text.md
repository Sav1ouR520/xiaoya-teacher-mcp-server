# 题干富文本（title_raw）支持矩阵

小雅平台的题干/描述富文本编辑器基于 **Draft.js**，`title_raw` 字段直接存 Draft.js 的 `{ blocks, entityMap }` 结构。以下支持矩阵通过 **Playwright 自动化摸取官方编辑器的 React props**（`blockRenderMap` + `customStyleMap`）得到，是平台承认的、不靠猜。

摸取时间：2026-04-14，课程域名 `fzrjxy.ai-augmented.com`。

---

## 结构回顾

```json
{
  "blocks": [
    {
      "text": "一行文本内容",
      "type": "unstyled",
      "inlineStyleRanges": [{"offset": 0, "length": 4, "style": "BOLD"}],
      "entityRanges": []
    }
  ],
  "entityMap": {}
}
```

- 每个 `block` = 编辑器里的一行（换行会拆成多个 block）
- `type`：决定这一行的段落样式（段落 / 标题 / 列表 / 代码块 ...）
- `inlineStyleRanges`：这一行里局部字符的样式（加粗 / 颜色 / 字号 ...），`offset/length` 以 UTF-16 code unit 计数，中文一个字一位
- `entityRanges` + `entityMap`：用于图片、链接等带元数据的内容

---

## Block Type（段落级样式）

15 种，均为 Draft.js 官方约定：

| type | 说明 | 典型用途 |
|---|---|---|
| `unstyled` | 普通段落 | 默认，推荐 |
| `header-one` 到 `header-six` | H1 至 H6 标题 | 章节标题 |
| `ordered-list-item` | 有序列表项 | 1. 2. 3. 的步骤列表 |
| `unordered-list-item` | 无序列表项 | • 点号列表 |
| `code-block` | 代码块 | 样例输入输出、代码片段 |
| `blockquote` | 引用 | 引用材料、提示 |
| `atomic` | 原子块 | 配合 entityMap 插入图片等 |
| `section` / `article` / `sticker` | 结构/装饰块 | 编辑器内部用，外部一般用不上 |

**实战结论**：`unstyled` + `header-*` + 列表 + `code-block` + `blockquote` 都可直接写入 title_raw，不会被拒。

**⚠️ 本次会话曾遇到 `code-block` + `create_code_question` 返回 HTTP 400**：根因是同时传了自定义 `max_memory=65536`（见本仓库 SKILL.md "编程题避坑" 节）。`code-block` 本身是平台支持的。

---

## Inline Style（行内字符样式）

### 1. 基础样式（Draft.js 默认）

| style | 渲染 |
|---|---|
| `BOLD` | **加粗** |
| `ITALIC` | *斜体* |
| `UNDERLINE` | <u>下划线</u> |
| `CODE` | `等宽代码` |
| `lineThrough` | ~~删除线~~ |
| `SUBSCRIPT` | 下标 |
| `SUPERSCRIPT` | 上标 |

### 2. 字号（17 档）

`fontSize-12` / `14` / `16` / `18` / `20` / `22` / `24` / `26` / `28` / `30` / `32` / `36` / `40` / `44` / `48` / `54` / `60`

写法：`{"style": "fontSize-24"}`

### 3. 字体

`fontFamily-msYaHei`（微软雅黑，默认）/ `song` / `xinSong` / `fangSong` / `kaiTi` / `heiTi` / `arial` / `arialBlack` / `timesNewRoman` / `courierNew` / `tahoma` / `verdana` / `sans-serif`

写法：`{"style": "fontFamily-courierNew"}`

### 4. 文字颜色 / 背景色

两套写法，平台都认：

**HEX 色板**（30 种）：`color-#ff6900` / `backgroundColor-#ffff02` 等。完整色板：
```
#ffffff #fdeeee #ffe1b2 #ffff02 #c8f0d6 #d3e8ff #dadbef #fedaec #d9d9d9
#f78da7 #ff6900 #fed670 #7bdcb5 #8ed1fc #8c7be9 #ee94f7 #abb8c3
#e06666 #bd5b22 #fcb900 #00d084 #0693e3 #4756fe #d041e1
#000000 #eb144c #ac2840 #c29632 #4aa36f #3374b1 #403ed6 #9900ef
```

**语义简写色**（8 对）：`color-red` / `color-red_less` / `color-orange` / `color-yellow` / `color-grass` / `color-green` / `color-blue` / `color-purple`，各自对应 `backgroundColor-*` 版本。

---

## Entity（带数据的内联内容）

编辑器加载了 **28 个 plugin**（图片、公式、链接、表格、视频、思维导图等）。通过 `atomic` block + `entityMap` 插入。目前 MCP 侧未封装 entity 构造工具，若需要图片/公式题干：

- 老师在网页上直接贴图/插公式（最稳）
- 或 MCP 后续补 helper（待办）

---

## 推荐的最小可用模板（出题用）

OJ 风格、学生基础弱、输出精简的场景，最稳的就是这套：

```json
{
  "blocks": [
    {"text": "【题目描述】", "type": "unstyled", "inlineStyleRanges": [{"offset": 0, "length": 6, "style": "BOLD"}]},
    {"text": "题目正文一行或多行。", "type": "unstyled", "inlineStyleRanges": []},
    {"text": "", "type": "unstyled", "inlineStyleRanges": []},
    {"text": "【输入格式】", "type": "unstyled", "inlineStyleRanges": [{"offset": 0, "length": 6, "style": "BOLD"}]},
    {"text": "输入说明。", "type": "unstyled", "inlineStyleRanges": []},
    {"text": "", "type": "unstyled", "inlineStyleRanges": []},
    {"text": "【样例输入】", "type": "unstyled", "inlineStyleRanges": [{"offset": 0, "length": 6, "style": "BOLD"}]},
    {"text": "3", "type": "code-block", "inlineStyleRanges": []},
    {"text": "1 2 3", "type": "code-block", "inlineStyleRanges": []},
    {"text": "", "type": "unstyled", "inlineStyleRanges": []},
    {"text": "【小提示】写在这里。", "type": "unstyled", "inlineStyleRanges": [{"offset": 0, "length": 5, "style": "BOLD"}]}
  ],
  "entityMap": {}
}
```

要点：

- **空行 = `text=""` 的 unstyled block**（Draft.js 不吃 `\n\n`，每一行必须是独立 block）
- **小标题加粗**用 `inlineStyleRanges` 包住整个 `【...】`
- **样例/代码**优先用 `code-block` block type，比 unstyled 更易读
- **offset/length 用 UTF-16 单位**，中文一个字算 1

---

## 被证明不能乱传的字段

| 字段 | 现象 | 正确做法 |
|---|---|---|
| `program_setting.max_memory` 自定义值（如 `65536`、`131072`） | `create_code_question` 返回 HTTP 400 "题目设置更新失败" | 不传，用默认值；参考代码避免 `from collections import Counter` 等吃内存的 import |
| `program_setting.max_time` 自定义值 | 同上，HTTP 400 | 不传 |
| `title_raw.blocks[].entityRanges` 指向不存在的 entity | 题目创建成功但渲染异常 | 要么全走 `entityMap`、要么不填 |

---

## 验证结论是否最新

若平台版本升级（右下角显示 `V2.2.4504`+），建议在新会话里用 Playwright 重跑以下脚本确认 `customStyleMap` / `blockRenderMap` 是否有变化：

```javascript
// 在登录后的备授课页面控制台跑：
const e = document.querySelector('.DraftEditor-root');
const fk = Object.keys(e).find(k => k.startsWith('__reactFiber'));
let f = e[fk];
while (f && !(f.memoizedProps?.customStyleMap)) f = f.return;
console.log('styleMap keys:', Object.keys(f.memoizedProps.customStyleMap));
console.log('blockMap keys:', [...f.memoizedProps.blockRenderMap.keys()]);
```
