---
name: xiaoya-teacher-skill
description: Use when the user explicitly needs to query, create, update, grade, or troubleshoot content inside 小雅教学平台 or xiaoya-teacher-mcp-server, including XiaoYa courses, resources, papers, questions, published tasks, student submissions, attendance, sign-in records, or MCP setup.
---

# 小雅教学助手

Help teachers operate XiaoYa through `xiaoya-teacher-mcp-server`. Use teacher-facing language: say course, paper, question, resource, student, and attendance; hide IDs unless troubleshooting requires them.

## Before Acting

1. If tools are missing or auth fails, read `references/setup.md`.
2. For any platform operation, identify the course first with `query_teacher_groups`.
3. If the user did not name the exact target, query candidates and let the teacher choose.
4. Before create/update/delete/grade/submit actions, summarize the pending change and ask for confirmation.
5. Do not invent platform data. Query again when a required field is missing.

## Workflow Map

Read `references/operations.md` before executing the matching workflow; it contains required ID chains, parameter sources, and failure handling.

| User intent | Start with | Then use |
|---|---|---|
| Create or edit a paper/question | `query_course_resources_summary` | [operations.md#papers-and-questions](references/operations.md#papers-and-questions) |
| Read courseware or teaching materials | `query_course_resources_summary` | [operations.md#reading-course-resources](references/operations.md#reading-course-resources) |
| Manage folders/resources | `query_course_resources_summary` | [operations.md#resource-management](references/operations.md#resource-management) |
| Grade submissions or attachments | `query_group_tasks` | [operations.md#grading](references/operations.md#grading) |
| Check attendance/sign-in | `query_group_classes`, `query_attendance_records` | [operations.md#attendance](references/operations.md#attendance) |
| Handle MCP/auth/setup errors | `server_status`, `auth_status` | `references/setup.md` |

## Non-Negotiable Rules

- Unpublished papers are course resources of type `ASSIGNMENT`; find them in resources, not task results.
- Published work uses `query_group_tasks` and `publish_id`; grading starts after publication.
- Course root creation needs the real root resource `id`, not `group_id`.
- `read_file_by_markdown` reads XiaoYa files with `paper_id + filename`; local files use `file_path`.
- `batch_create_questions` is not transactional. Always inspect `data.failed_items` on partial failure.
- For code questions, only pass necessary `program_setting` fields unless the teacher explicitly requests limits.
- For manual grading, use the exact ID chain from `operations.md#grading`; do not substitute `answer_id`, `record_id`, or `quote_id` for each other.

## References

- [operations.md](references/operations.md): tool workflows, parameters, and XiaoYa-specific pitfalls.
- [title_rich_text.md](references/title_rich_text.md): `title_raw` Draft.js block/style reference for rich question text.
- [setup.md](references/setup.md): MCP installation, auth, transport, and troubleshooting.
