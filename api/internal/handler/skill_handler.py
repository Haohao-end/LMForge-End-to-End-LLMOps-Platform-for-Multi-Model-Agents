from __future__ import annotations

import io
from dataclasses import dataclass
from uuid import UUID

from flask import redirect, request, send_file
from injector import inject

from internal.schema.skill_schema import (
    GetSkillsCategoriesResp,
    GetSkillsWithPageReq,
    SkillPackageResp,
)
from internal.service.skill_service import SkillService
from pkg.paginator import PageModel
from pkg.response import success_json, validate_error_json


@inject
@dataclass
class SkillHandler:
    """技能包处理器。"""

    skill_service: SkillService

    def get_skill_categories(self):
        """获取技能分类统计。"""
        resp = GetSkillsCategoriesResp()
        return success_json(resp.dump(self.skill_service.get_skill_categories()))

    def get_skills_with_page(self):
        """获取技能包列表。"""
        req = GetSkillsWithPageReq(request.args)
        if not req.validate():
            return validate_error_json(req.errors)

        skills, paginator = self.skill_service.get_skill_packages_with_page(req)
        resp = SkillPackageResp(many=True)
        return success_json(PageModel(list=resp.dump(skills), paginator=paginator))

    def get_skill_package(self, skill_id: UUID):
        """获取技能包详情。"""
        skill_package = self.skill_service.get_skill_package(skill_id)
        resp = SkillPackageResp()
        return success_json(resp.dump(skill_package))

    def get_skill_package_icon(self, skill_id: UUID):
        """获取技能包图标。"""
        icon, mimetype, icon_url = self.skill_service.get_skill_package_icon(skill_id)
        if icon_url:
            return redirect(icon_url)
        if icon is None:
            icon = b""
        return send_file(io.BytesIO(icon), mimetype or "application/octet-stream")
