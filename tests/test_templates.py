"""Tests for runtime_generator templates."""
import pytest, ast
from runtime_generator.generator import EntityDef, FieldDef
from runtime_generator import templates as T

@pytest.fixture
def lead():
    return EntityDef(name="Lead", table_name="lead", fields=[
        FieldDef(name="id", type="string", primary_key=True),
        FieldDef(name="name", type="string"),
    ])

class TestEnginePy:
    def test_valid_syntax(self, lead):
        code = T.engine_py("test", [lead])
        ast.parse(code)
    def test_contains_class(self, lead):
        assert "class RuntimeEngine" in T.engine_py("test", [lead])
    def test_action_map(self, lead):
        result = T.engine_py("test", [lead])
        assert "list_lead" in result

class TestMcpServerPy:
    def test_valid_syntax(self, lead):
        ast.parse(T.mcp_server_py("test", [lead]))
    def test_has_tool_definitions(self, lead):
        assert "TOOL_DEFINITIONS" in T.mcp_server_py("test", [lead])

class TestModelsPy:
    def test_valid_syntax(self, lead):
        ast.parse(T.models_py([lead]))
    def test_has_class(self, lead):
        assert "class LeadModel" in T.models_py([lead])

class TestRuntimeYaml:
    def test_generates_yaml(self, lead):
        r = T.runtime_yaml("x", "d", "a", [lead], {})
        assert "name:" in r and "database:" in r
    def test_valid_yaml(self, lead):
        import yaml; yaml.safe_load(T.runtime_yaml("x", "d", "a", [lead], {}))

class TestDomainYaml:
    def test_generates_yaml(self, lead):
        r = T.domain_yaml(lead)
        assert "Lead" in r and "lead" in r
    def test_valid_yaml(self, lead):
        import yaml; yaml.safe_load(T.domain_yaml(lead))

class TestWorkflowYaml:
    def test_generates(self, lead):
        r = T.example_workflow_yaml("proj", [lead])
        assert "proj" in r and "workflow" in r

class TestEndToEnd:
    def test_save_generates_valid_files(self, tmp_path, lead):
        from runtime_generator.generator import RuntimeGenerator, GeneratorConfig
        cfg = GeneratorConfig(name="e2e", output_dir=tmp_path)
        g = RuntimeGenerator(cfg); g.add_entity(lead); g.save()
        base = tmp_path / "e2e"
        ast.parse((base / "mcp_server.py").read_text())
        ast.parse((base / "app" / "runtime" / "engine.py").read_text())
        ast.parse((base / "app" / "infrastructure" / "models.py").read_text())
