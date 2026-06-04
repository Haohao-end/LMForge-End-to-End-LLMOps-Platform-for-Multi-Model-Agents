from __future__ import annotations


def test_skill_public_management_routes_should_be_registered(app):
    rules = {rule.rule for rule in app.url_map.iter_rules() if rule.endpoint != "static"}

    assert "/skills" in rules
    assert "/skills/categories" in rules
    assert "/skills/<uuid:skill_id>" in rules
    assert "/skills/<uuid:skill_id>/icon" in rules
    assert "/skills/<uuid:skill_id>/versions" in rules
    assert "/skills/<uuid:skill_id>/enable" in rules
    assert "/skills/<uuid:skill_id>/disable" in rules
    assert "/skills/<uuid:skill_id>/sync" in rules
    assert "/skills/<uuid:skill_id>/rollback" in rules
