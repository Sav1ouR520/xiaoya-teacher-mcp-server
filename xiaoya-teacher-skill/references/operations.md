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

For rich code-question text, use `title_raw`; see `title_rich_text.md`.

### Paper Settings

After question creation, use:

- `query_paper_summary` to report question count, type counts, and total score.
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
3. For manual grading or answer inspection, call `query_preview_student_paper(group_id, paper_id, mark_mode_id, publish_id, record_id, detail_level="full", parse_mode="plain")`.
4. Read `mark_paper_record_id` from the preview result. For each manually graded question, read `question_id`, `answer_id`, maximum `score`, and current answer content.
5. For attachment questions, read `attachments[].quote_id` from the matching full-preview question. Do not use `answer_id`, `question_id`, or `record_id` as `quote_id`.
6. Call `get_answer_file(quote_id, save_path=...)` for images/PDFs/large files so the file lands on disk. Use base64 mode only for small text extraction.
7. After teacher confirms suggested scores/comments, call `grade_student_question(group_id, publish_id, mark_paper_record_id, record_id, question_id, answer_id, score, comment)`.
8. After all manual questions for that student are graded, call `submit_student_mark(group_id, answer_record_id=record_id, mark_mode_id, mark_paper_record_id)`.

Automatically scored choice/true-false/fill-blank/code questions usually do not need `grade_student_question`.

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
