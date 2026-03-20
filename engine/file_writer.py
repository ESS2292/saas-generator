import os


class GeneratedProjectError(ValueError):
    pass


def _resolve_output_path(app_root, file_path):
    if os.path.isabs(file_path):
        raise GeneratedProjectError(f"Absolute output paths are not allowed: {file_path}")

    normalized_path = os.path.normpath(file_path)
    if normalized_path.startswith("..") or normalized_path == ".":
        raise GeneratedProjectError(f"Unsafe output path rejected: {file_path}")

    app_root_abs = os.path.abspath(app_root)
    full_path = os.path.abspath(os.path.join(app_root_abs, normalized_path))
    if os.path.commonpath([app_root_abs, full_path]) != app_root_abs:
        raise GeneratedProjectError(f"Output path escapes project root: {file_path}")

    return full_path, normalized_path


def _validate_required_files(file_blocks):
    generated_files = {file_path for file_path, _ in file_blocks}
    required_files = {"backend/main.py", "frontend/package.json"}
    missing_files = sorted(required_files - generated_files)
    if missing_files:
        missing_str = ", ".join(missing_files)
        raise GeneratedProjectError(f"Generated output is missing required files: {missing_str}")


def save_project_files(file_blocks, app_root="generated_app", validate_required=True):
    if not file_blocks:
        raise GeneratedProjectError("No files were provided for project generation.")
    if validate_required:
        _validate_required_files(file_blocks)

    saved_files = []

    for file_path, content in file_blocks:
        full_path, normalized_path = _resolve_output_path(app_root, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        saved_files.append(normalized_path)
        print(f"Saved: {full_path}")

    return saved_files


def save_project(output_text, app_root="generated_app"):
    raise GeneratedProjectError("Freeform code output is no longer supported. Use manifest-based generation.")
