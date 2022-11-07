from trustregistry import models


def test_actor():
    actor = models.Actor(
        id="mickey-mouse",
        name="Mickey Mouse",
        roles="verifier, issuer",
        didcomm_invitation="xyz",
        did="abc",
        group_id="GroupId",
    )

    assert actor.id == "mickey-mouse"
    assert actor.name == "Mickey Mouse"
    assert actor.roles == "verifier, issuer"
    assert actor.didcomm_invitation == "xyz"
    assert actor.did == "abc"
    assert actor.group_id == "GroupId"


def test_schema():
    schema = models.Schema(did="abc", name="doubleaceschema", version="0.4.20")

    assert schema.did == "abc"
    assert schema.name == "doubleaceschema"
    assert schema.version == "0.4.20"
