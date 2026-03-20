import re
import subprocess
from uuid import uuid4
from pathlib import Path

from engine.runtime_env import configure_runtime_environment

configure_runtime_environment()

from crewai import Crew

from agents.architect import architect
from agents.code_generator import code_generator
from deployment.deploy import deploy_online
from docker_runner.docker_runner import build_and_run_docker
from engine.file_writer import GeneratedProjectError
from engine.frontend_verifier import verify_generated_frontend_build, verify_generated_frontend_preview
from engine.generate_code import create_generate_code_task
from engine.intake import analyze_product_request
from engine.plan import create_plan_task
from engine.repair import repair_project_for_failure, repair_project_from_output
from engine.runtime_verifier import verify_generated_backend_runtime
from engine.spec_refiner import refine_product_spec
from memory.project_memory import save_memory
from tests.auto_test import run_tests
from tests.debug_loop import recursive_debug


class PipelineStageError(Exception):
    def __init__(self, stage, message):
        super().__init__(message)
        self.stage = stage


def remove_existing_backend_container():
    subprocess.run(
        ["docker", "rm", "-f", "saas_backend_container"],
        capture_output=True,
        text=True,
    )


def build_and_test_generated_app(app_root="generated_app"):
    try:
        verify_generated_backend_runtime(app_root=app_root)
    except GeneratedProjectError as exc:
        raise PipelineStageError("backend_runtime", str(exc)) from exc

    try:
        verify_generated_frontend_build(app_root=app_root)
    except GeneratedProjectError as exc:
        raise PipelineStageError("frontend_build", str(exc)) from exc

    try:
        verify_generated_frontend_preview(app_root=app_root, install_deps=False, build_first=False)
    except GeneratedProjectError as exc:
        raise PipelineStageError("frontend_preview", str(exc)) from exc

    try:
        remove_existing_backend_container()
        build_and_run_docker(app_folder=app_root)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise PipelineStageError("docker_backend", str(exc)) from exc

    try:
        return run_tests()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise PipelineStageError("integration_tests", str(exc)) from exc


def rebuild_generated_project(output_text, app_root="generated_app", intake_context=None, spec_brief=None):
    repaired = repair_project_from_output(
        output_text,
        app_root=app_root,
        intake_context=intake_context,
        spec_brief=spec_brief,
    )
    return repaired


def targeted_repair_generated_project(
    output_text,
    failure_stage,
    error_text="",
    app_root="generated_app",
    intake_context=None,
    spec_brief=None,
):
    repaired = repair_project_for_failure(
        output_text,
        app_root=app_root,
        intake_context=intake_context,
        spec_brief=spec_brief,
        failure_stage=failure_stage,
        error_text=error_text,
    )
    return repaired


def app_root_for_idea(user_idea, base_dir="generated_apps"):
    slug = re.sub(r"[^a-z0-9]+", "-", user_idea.lower()).strip("-")
    slug = slug[:48] or "generated-app"
    return str(Path(base_dir) / f"{slug}-{uuid4().hex[:8]}")


def generate_saas_app(
    user_idea,
    app_root="generated_app",
    run_verification=True,
    auto_deploy=False,
    max_retries=3,
):
    if not user_idea or not user_idea.strip():
        raise ValueError("No SaaS idea entered.")

    user_idea = user_idea.strip()
    result_text = ""
    latest_error = ""
    tests_passed = False
    deployed = False
    retries_used = 0

    save_memory({"type": "user_idea", "content": user_idea})

    intake_context = analyze_product_request(user_idea)
    spec_brief = refine_product_spec(user_idea, intake_context)

    save_memory({"type": "intake_context", "idea": user_idea, "content": intake_context})
    save_memory({"type": "spec_brief", "idea": user_idea, "content": spec_brief})

    plan_saas = create_plan_task(architect, user_idea, intake_context=intake_context, spec_brief=spec_brief)
    generate_code_task = create_generate_code_task(
        code_generator,
        user_idea,
        plan_saas,
        intake_context=intake_context,
        spec_brief=spec_brief,
    )

    crew = Crew(agents=[architect, code_generator], tasks=[plan_saas, generate_code_task])
    crew_result = crew.kickoff()
    result_text = str(crew_result)

    save_memory({"type": "generated_output", "idea": user_idea, "content": result_text})

    try:
        repaired = rebuild_generated_project(
            result_text,
            app_root=app_root,
            intake_context=intake_context,
            spec_brief=spec_brief,
        )
        result_text = repaired["manifest_text"]
    except GeneratedProjectError as exc:
        latest_error = str(exc)
        return {
            "success": False,
            "app_root": app_root,
            "intake_context": intake_context,
            "spec_brief": spec_brief,
            "raw_output": str(crew_result),
            "manifest_text": "",
            "manifest": None,
            "tests_passed": False,
            "deployed": False,
            "latest_error": latest_error,
            "retries_used": retries_used,
            "saved_files_count": 0,
        }

    if run_verification:
        try:
            tests_passed = build_and_test_generated_app(app_root=app_root)
        except PipelineStageError as exc:
            latest_error = str(exc)
            try:
                repaired = targeted_repair_generated_project(
                    result_text,
                    failure_stage=exc.stage,
                    error_text=latest_error,
                    app_root=app_root,
                    intake_context=intake_context,
                    spec_brief=spec_brief,
                )
                result_text = repaired["manifest_text"]
                tests_passed = build_and_test_generated_app(app_root=app_root)
            except (GeneratedProjectError, PipelineStageError) as repair_exc:
                latest_error = str(repair_exc)

        while not tests_passed and retries_used < max_retries:
            retries_used += 1
            try:
                repaired = rebuild_generated_project(
                    result_text,
                    app_root=app_root,
                    intake_context=intake_context,
                    spec_brief=spec_brief,
                )
                result_text = repaired["manifest_text"]
                tests_passed = build_and_test_generated_app(app_root=app_root)
                if tests_passed:
                    break
            except (GeneratedProjectError, PipelineStageError) as exc:
                latest_error = str(exc)
                failure_stage = exc.stage if isinstance(exc, PipelineStageError) else "scaffold_validation"
                try:
                    repaired = targeted_repair_generated_project(
                        result_text,
                        failure_stage=failure_stage,
                        error_text=latest_error,
                        app_root=app_root,
                        intake_context=intake_context,
                        spec_brief=spec_brief,
                    )
                    result_text = repaired["manifest_text"]
                    tests_passed = build_and_test_generated_app(app_root=app_root)
                    if tests_passed:
                        break
                except (GeneratedProjectError, PipelineStageError) as targeted_exc:
                    latest_error = str(targeted_exc)

            docker_logs = subprocess.run(
                ["docker", "logs", "saas_backend_container"],
                capture_output=True,
                text=True,
            ).stdout.strip()
            if not docker_logs:
                docker_logs = latest_error or "No container logs were available."

            corrected_code = recursive_debug(result_text, docker_logs)
            result_text = str(corrected_code)
            save_memory(
                {
                    "type": "debug_attempt",
                    "idea": user_idea,
                    "attempt": retries_used,
                    "errors": docker_logs,
                    "corrected_output": result_text,
                }
            )

            try:
                repaired = rebuild_generated_project(
                    result_text,
                    app_root=app_root,
                    intake_context=intake_context,
                    spec_brief=spec_brief,
                )
                result_text = repaired["manifest_text"]
            except GeneratedProjectError as exc:
                latest_error = str(exc)
                continue

            try:
                tests_passed = build_and_test_generated_app(app_root=app_root)
                latest_error = ""
            except PipelineStageError as exc:
                latest_error = str(exc)
                tests_passed = False
    else:
        tests_passed = False

    manifest = None
    saved_files_count = 0
    try:
        repaired = rebuild_generated_project(
            result_text,
            app_root=app_root,
            intake_context=intake_context,
            spec_brief=spec_brief,
        )
        manifest = repaired["manifest"]
        saved_files_count = len(repaired["saved_files"])
    except GeneratedProjectError as exc:
        latest_error = str(exc)

    if tests_passed and auto_deploy:
        try:
            deploy_online(app_folder=app_root)
            deployed = True
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            latest_error = str(exc)

    return {
        "success": manifest is not None and (tests_passed if run_verification else True),
        "app_root": app_root,
        "intake_context": intake_context,
        "spec_brief": spec_brief,
        "raw_output": str(crew_result),
        "manifest_text": result_text,
        "manifest": manifest,
        "tests_passed": tests_passed,
        "deployed": deployed,
        "latest_error": latest_error,
        "retries_used": retries_used,
        "saved_files_count": saved_files_count,
    }
