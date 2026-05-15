from typer_utils.utils import is_cmd_exists


def test_cmd():
    result = is_cmd_exists("open-webui-pipelines")
    assert result is True
