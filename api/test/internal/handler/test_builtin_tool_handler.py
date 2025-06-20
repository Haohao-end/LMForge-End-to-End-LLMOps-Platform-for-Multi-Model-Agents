from pkg.response import HttpCode
import pytest

class TestBuiltinToolHandler:
    """内置工具处理器测试类"""

    def test_get_categories(self,client):
        """测试所有分类信息"""
        resp = client.get("/builtin-tools/categories")
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.SUCCESS
        assert len(resp.json.get("data")) > 0

    def test_get_builtin_tools(self,client):
        """测试获取所有内置工具"""
        resp = client.get("/builtin-tools")
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.SUCCESS
        assert len(resp.json.get("data")) > 0

    @pytest.mark.parametrize(
        "provider_name,tool_name",
        [
            ("google","google_serper")
        ]
    )
    def test_get_provider_tool(self,provider_name,tool_name,client):
        """测试获取指定工具信息接口"""
        resp = client.get(f"/builtin-tools/{provider_name}/tools/{tool_name}")
        assert resp.status_code == 200
        if provider_name == resp.json.get("data").get("name"):
            assert resp.json.get("code") == HttpCode.SUCCESS
            assert resp.json.get("data").get("name") == tool_name


    @pytest.mark.parametrize(
        "provider_name",
        ["google","haohao"]
    )
    def test_get_provider_icon(self,provider_name,client):
        """测试根据提供商名字获取icon接口"""
        resp = client.get(f"/builtin-tools/{provider_name}/icon")
        assert resp.status_code == 200
        if provider_name == "haohao":
            assert resp.json.get("code") == HttpCode.NOT_FOUND