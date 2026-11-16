# lba-fixture Specification

## Purpose
TBD - created by archiving change bootstrap-projet. Update Purpose after archive.

## Requirements

### Requirement: Reproducible LBA fixture
`scripts/make_fixture.py` SHALL écrire le premier bloc de `ft_test_results.json` dans `tests/fixtures/lba_search.json` (`ensure_ascii=False`, `indent=1`) ; la fixture SHALL être committée.

#### Scenario: Fixture content
- **WHEN** un test charge `tests/fixtures/lba_search.json`
- **THEN** il contient 16 `jobs` et 150 `recruiters`
