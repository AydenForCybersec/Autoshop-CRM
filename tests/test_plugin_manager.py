import json
import sys
from pathlib import Path

import pytest

from autoshop_crm.plugins import PluginMixin
from autoshop_crm.plugins.manager import PluginManager


@pytest.fixture
def plugin_dir(tmp_path):
    """Create a temp plugins directory with one valid plugin."""
    p = tmp_path / "my_plugin"
    p.mkdir()
    (p / "plugin.json").write_text(json.dumps({
        "id": "my_plugin",
        "name": "My Plugin",
        "version": "1.0.0",
        "description": "Test plugin.",
        "author": "Test",
        "permissions": [],
        "declares_permissions": [],
    }))
    (p / "plugin.py").write_text(
        "from autoshop_crm.plugins import PluginMixin\n"
        "class MyPlugin(PluginMixin):\n"
        "    pass\n"
    )
    return tmp_path


def test_discover_finds_valid_plugin(plugin_dir):
    mgr = PluginManager(plugins_dir=plugin_dir)
    discovered = mgr.discover()
    assert "my_plugin" in discovered


def test_discover_skips_dir_without_manifest(tmp_path):
    bad = tmp_path / "bad_plugin"
    bad.mkdir()
    (bad / "plugin.py").write_text("# no manifest")
    mgr = PluginManager(plugins_dir=tmp_path)
    assert "bad_plugin" not in mgr.discover()


def test_load_plugin_instantiates_mixin(plugin_dir):
    mgr = PluginManager(plugins_dir=plugin_dir)
    manifests = mgr.discover()
    instance = mgr._load_plugin(manifests["my_plugin"])
    assert isinstance(instance, PluginMixin)
    assert instance.plugin_id == "my_plugin"


def test_load_plugin_with_syntax_error_does_not_raise(tmp_path):
    p = tmp_path / "broken"
    p.mkdir()
    (p / "plugin.json").write_text(json.dumps({
        "id": "broken", "name": "Broken", "version": "1.0.0",
        "description": "", "author": "", "permissions": [], "declares_permissions": [],
    }))
    (p / "plugin.py").write_text("this is not valid python !!!")
    mgr = PluginManager(plugins_dir=tmp_path)
    manifests = mgr.discover()
    result = mgr._load_plugin(manifests["broken"])
    assert result is None
