def test_discovery_fixtures_load(discovery_emails):
    assert len(discovery_emails) == 3
    assert "Snowflake" in discovery_emails[0]["body"]


def test_followup_fixtures_load(followup_emails):
    assert len(followup_emails) == 1
    assert "meeting" in followup_emails[0]["subject"].lower()


def test_poc_fixtures_load(poc_emails):
    assert len(poc_emails) == 1


def test_proposal_fixtures_load(proposal_emails):
    assert len(proposal_emails) == 1
    assert "proposal" in proposal_emails[0]["subject"].lower()
