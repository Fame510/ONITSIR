"""CLI smoke tests."""
import pytest

from onitsir import cli


def test_cli_roster(capsys):
    rc = cli.main(["roster"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "164 specialists" in out


def test_cli_crew_match(capsys):
    rc = cli.main(["crew", "reddit community marketing growth"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Staffed crew" in out


def test_cli_crew_no_match(capsys):
    rc = cli.main(["crew", "zzzq unmatchable termxyz"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "No confident specialist match" in out


def test_cli_run_ships(capsys):
    rc = cli.main(["run", "launch a marketing content campaign"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Mission SHIPPED" in out


def test_cli_requires_subcommand():
    with pytest.raises(SystemExit):
        cli.main([])
