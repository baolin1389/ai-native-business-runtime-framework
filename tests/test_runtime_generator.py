"""Tests for runtime_generator.generator."""
import pytest
from runtime_generator.generator import RuntimeGenerator, GeneratorConfig, FieldDef, EntityDef, RelationDef

@pytest.fixture
def lead():
    return EntityDef(name="Lead", table_name="lead", fields=[FieldDef(name="id", type="string", primary_key=True)])

class TestGeneratorConfig:
    def test_name_required(self):
        cfg = GeneratorConfig(name="x")
        assert cfg.name == "x"
    def test_defaults(self):
        cfg = GeneratorConfig(name="x")
        assert cfg.include_examples is True
        assert cfg.author == ""

class TestRuntimeGenerator:
    def test_rejects_string(self):
        with pytest.raises(TypeError): RuntimeGenerator("not-a-config")
    def test_accepts_config(self):
        cfg = GeneratorConfig(name="test")
        g = RuntimeGenerator(cfg)
        assert g.config is cfg
    def test_add_entity(self, lead):
        g = RuntimeGenerator(GeneratorConfig(name="t"))
        g.add_entity(lead)
        assert len(g.entities) == 1
    def test_save_no_raise(self, tmp_path, lead):
        cfg = GeneratorConfig(name="s", output_dir=tmp_path)
        g = RuntimeGenerator(cfg); g.add_entity(lead); g.save()

class TestCLIGenerate:
    def test_writes_files(self, tmp_path, lead):
        cfg = GeneratorConfig(name="cli-test", output_dir=tmp_path)
        g = RuntimeGenerator(cfg); g.add_entity(lead); g.save()
        base = tmp_path / "cli-test"
        assert (base / "app" / "runtime" / "engine.py").exists()
        assert (base / "app" / "infrastructure" / "models.py").exists()
        assert (base / "mcp_server.py").exists()
