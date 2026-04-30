from autoshop_crm.plugins import PluginMixin


class MinimalPlugin(PluginMixin):
    pass


def test_default_blueprint_is_none():
    assert MinimalPlugin().get_blueprint() is None


def test_default_nav_items_is_empty():
    assert MinimalPlugin().get_nav_items() == []


def test_default_dashboard_widgets_is_empty():
    assert MinimalPlugin().get_dashboard_widgets() == []


def test_default_settings_panel_is_none():
    assert MinimalPlugin().get_settings_panel() is None


def test_default_template_vars_is_empty():
    assert MinimalPlugin().get_template_vars() == {}


def test_on_install_does_not_raise():
    MinimalPlugin().on_install()


def test_on_uninstall_does_not_raise():
    MinimalPlugin().on_uninstall()
