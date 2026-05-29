from __future__ import annotations


def test_skill_public_management_routes_should_not_be_registered(app):
    rules = {rule.rule for rule in app.url_map.iter_rules() if rule.endpoint != "static"}

    assert "/skills" in rules
    assert "/skills/categories" in rules
    assert "/skills/<uuid:skill_id>" in rules
    assert "/skills/<uuid:skill_id>/icon" in rules

    assert "/skills/<uuid:skill_id>/versions" not in rules
    assert "/skills/<uuid:skill_id>/enable" not in rules
    assert "/skills/<uuid:skill_id>/disable" not in rules
    assert "/skills/<uuid:skill_id>/sync" not in rules
    assert "/skills/<uuid:skill_id>/rollback" not in rules
