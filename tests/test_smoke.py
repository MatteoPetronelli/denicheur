import denicheur
from denicheur.__main__ import main


def test_package_imports():
    assert denicheur.__doc__


def test_stub_command(capsys):
    assert main(["run"]) == 0
    assert "non implémenté" in capsys.readouterr().out
