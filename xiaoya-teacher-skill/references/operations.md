# XiaoYa Operations Reference

Use this file only after the `xiaoya-teacher-skill` has triggered and the user is performing a XiaoYa platform operation.

## Contents

- [Papers And Questions](#papers-and-questions)
- [Reading Course Resources](#reading-course-resources)
- [Resource Management](#resource-management)
- [Grading](#grading)
- [Attendance](#attendance)
- [Failure Handling](#failure-handling)

## Papers And Questions

### Locate Or Create A Paper

- Existing unpublished paper: call `query_course_resources_summary` or `query_course_resources(detail_level="full")`; choose a resource whose type is assignment and has `paper_id`.
- Published paper/task: call `query_group_tasks`; keep `paper_id` and `publish_id`.
- New paper: call `query_course_resources_summary` to choose a folder, then `create_course_resource(type_val=7)` / `ResourceType.ASSIGNMENT`.
- Root folder pitfall: `parent_id` must be the root resource `id`, not `group_id`. If unsure, call `query_resource_attributes(group_id, resource_id)`.
- After creation, confirm `paper_id`. If missing, query attributes or re-query resources by the new resource name. Do not create questions without `paper_id`.

### Collect Requirements

Confirm question type, count, score, source material, and randomization/required settings. If the teacher pasted full questions, convert them into a structured draft and confirm once.

All question models require `description`. If the teacher did not provide one, add a short explanation or grading note.

### Question Tool Selection

| Case | Tool | Notes |
|---|---|---|
| Single question | `create_*_question` | Use the type-specific tool |
| Mixed batch, includes code | `batch_create_questions` | Non-transactional; read `failed_items` |
| Official batch import | `office_create_questions` | Uses official schema, not single-question schema |

`office_create_questions` schema differs from single-question tools. Do not pass `options`. Use `answer_items` with `seqno/context` and `standard_answers`; for fill blanks include the scoring fields expected by the model.

### Code Questions

Minimum `program_setting`: `language`, `code_answer`, `in_cases`; set `answer_language` explicitly for multi-language questions. Each `in_cases` item contains only input, for example `{"in": "1 2"}`. Do not send `out`.

Do not override `max_memory`, `max_time`, `debug_count`, or `runcase_count` unless the teacher explicitly asks. Custom limits have caused platform HTTP 400 failures.

For rich code-question text, prefer `title_md` when the source is Markdown. Use `title_assets` for images/attachments referenced as `asset://id`. Use `title_raw` only when you need exact Draft.js control; see `title_rich_text.md`.

### Paper Settings

After question creation, use:

- `query_paper_summary` to report question count, type counts, and total score. Use `query_paper(..., detail_level="full", parse_mode="markdown")` when the next step is AI editing or round-tripping rich text.
- `configure_paper_basics` for required, question shuffle, option shuffle, and score mode.
- `update_paper_question_order` for order changes.
- `update_paper_randomization` for randomization-only changes.

## Reading Course Resources

`read_file_by_markdown` has two modes:

- XiaoYa resource: pass `paper_id` and `filename`.
- Local file: pass `file_path`.

Do not pass `resource_id` to `read_file_by_markdown`. If a summary item lacks `paper_id` or filename, call `query_course_resources(detail_level="full")` or `query_resource_attributes` first.

## Resource Management

Start with `query_course_resources_summary` so the teacher can choose the resource.

| Action | Tool |
|---|---|
| Create folder/note/assignment | `create_course_resource` |
| Rename | `update_resource_name` |
| Move | `move_resource` |
| Sort | `update_resource_sort` |
| Show/hide | `batch_update_resource_visibility` |
| Download permission | `batch_update_resource_download` |
| Delete | `delete_course_resource` |

Confirm destructive or visibility-changing operations before calling the tool.

## Grading

Use this chain exactly:

1. `query_group_tasks(group_id)` to choose a published task and get `paper_id` + `publish_id`.
2. `query_test_result(group_id, paper_id, publish_id, detail_level="full")` to get `mark_mode_id` and each student's `record_id`.
3. For agent-assisted grading, call `get_student_grading_bundle(group_id, paper_id, mark_mode_id, publish_id, record_id, save_dir=optional)`. It returns only `grading_context` and manually graded short-answer/attachment questions; auto-scored questions, empty fields, `quote_id`, file size, and cache state are omitted.
4. Review the answer text and local attachment `file_path` values.
5. After teacher confirms suggested scores/comments, call `grade_student_paper(grading_context=bundle.data.grading_context, grades=[...])`.

Low-level fallback:

- For a single-question correction, call `query_preview_student_paper(group_id, paper_id, mark_mode_id, publish_id, record_id, detail_level="full", parse_mode="plain")`. Use `parse_mode="markdown"` only when the answer content will be edited or reused as Markdown.
- For attachment questions, call `get_answer_file(quote_id, save_path=...)` only when the bundle did not already provide a usable `file_path`. Use base64 mode only for small text extraction.
- `get_answer_file` now fetches real files through `file_down/v2`; if the server returns an HTML preview page instead of binary content, the tool returns a structured error and the caller should retry or switch to bundle-based local cache files.
- To grade one question manually, call `grade_student_question(...)`, then `submit_student_mark(...)` after all required manual questions are graded.

Automatically scored choice/true-false/fill-blank/code questions usually do not need `grade_student_question`.

If a student's mark has already been submitted and the teacher confirms a change, call `withdraw_student_mark(group_id, answer_record_id=record_id, mark_mode_id, mark_paper_record_id)` first. Then re-grade the affected question and call `submit_student_mark` again. For a single tool call, use `revise_student_mark(..., allow_reopen=true, submit_after=true)` only after the teacher explicitly confirms reopening a submitted grade.

## Attendance

1. `query_group_classes(group_id)` returns class names, IDs, and member counts.
2. `query_attendance_records(group_id)` returns sign-in records, including `id`, `course_id`, `class_id`, time fields, and `register_count`.
3. For a specific attendance summary, call `query_single_attendance_students(group_id, register_id, course_id)`.

Do not claim complete attendance totals from the record list alone. Compute status counts from `query_single_attendance_students`. Treat leave as the sum of leave-like statuses returned by the platform; present unknown statuses explicitly instead of guessing.

## Failure Handling

- Service question: call `server_status`.
- Auth question: call `auth_status(refresh=true)` when credentials are available.
- Tool missing or MCP not configured: read `setup.md`.
- Partial batch question failure: report each `data.failed_items[]` entry and ask whether to retry failed questions or delete successful ones.
- Code question HTTP 400: remove custom time/memory settings first; then retry after teacher confirmation.
