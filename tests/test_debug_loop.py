from tests import debug_loop


class DummyTaskOutput:
    def __str__(self):
        return '{"app_name":"Fixed","slug":"fixed","tagline":"x","summary":"y","theme":{"primary_color":"#0f766e","accent_color":"#f59e0b","surface_color":"#ecfeff"},"dashboard":{"headline":"Head","subheadline":"Sub","sections":[{"title":"One","description":"Desc"}]},"data_model":[{"name":"Thing","fields":[{"name":"name","type":"string"}]}],"api_routes":[{"path":"/things","method":"GET","summary":"List"}],"sample_records":[{"title":"Sample","status":"active"}]}'


class DummyTask:
    last_description = None

    def __init__(self, **kwargs):
        DummyTask.last_description = kwargs["description"]

    def execute_sync(self, agent=None):
        return DummyTaskOutput()


def test_recursive_debug_includes_current_code_and_errors(monkeypatch):
    monkeypatch.setattr(debug_loop, "Task", DummyTask)

    result = debug_loop.recursive_debug("CURRENT CODE", "TRACEBACK")

    assert "CURRENT CODE" in DummyTask.last_description
    assert "TRACEBACK" in DummyTask.last_description
    assert '"app_name":"Fixed"' in result
