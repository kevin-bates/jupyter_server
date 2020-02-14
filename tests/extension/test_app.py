import pytest

from jupyter_server.serverapp import ServerApp
from jupyter_server.extension.application import ExtensionApp


def test_instance_creation(make_mock_extension_app, template_dir):
    mock_extension = make_mock_extension_app()
    assert mock_extension.static_paths == []
    assert mock_extension.template_paths == [str(template_dir)]
    assert mock_extension.settings == {}
    assert mock_extension.handlers == []


def test_initialize(serverapp, make_mock_extension_app):
    mock_extension = make_mock_extension_app()
    mock_extension.initialize(serverapp)
    # Check that settings and handlers were added to the mock extension.
    assert isinstance(mock_extension.serverapp, ServerApp)
    assert len(mock_extension.settings) > 0
    assert len(mock_extension.handlers) > 0


traits = [
    ('static_paths', ['test']),
    ('template_paths', ['test']),
    ('custom_display_url', '/test_custom_url'),
    ('default_url', '/test_url')
]


@pytest.mark.parametrize(
    'trait_name,trait_value',
    traits
)
def test_instance_creation_with_instance_args(trait_name, trait_value, make_mock_extension_app):
    kwarg = {}
    kwarg.setdefault(trait_name, trait_value)
    mock_extension = make_mock_extension_app(**kwarg)
    assert getattr(mock_extension, trait_name) == trait_value


@pytest.mark.parametrize(
    'trait_name,trait_value',
    traits
)
def test_instance_creation_with_argv(serverapp, trait_name, trait_value, make_mock_extension_app):
    kwarg = {}
    kwarg.setdefault(trait_name, trait_value)
    argv = [
        '--MockExtensionApp.{name}={value}'.format(name=trait_name, value=trait_value)
    ]
    mock_extension = make_mock_extension_app()
    mock_extension.initialize(serverapp, argv=argv)
    assert getattr(mock_extension, trait_name) == trait_value


def test_extensionapp_load_config_file(config_file, serverapp, extended_serverapp):
    # Assert default config_file_paths is the same in the app and extension.
    assert extended_serverapp.config_file_paths == serverapp.config_file_paths
    assert extended_serverapp.config_file_name == 'jupyter_mockextension_config'
    assert extended_serverapp.config_dir == serverapp.config_dir
    # Assert that the trait is updated by config file
    assert extended_serverapp.mock_trait == 'config from file'
