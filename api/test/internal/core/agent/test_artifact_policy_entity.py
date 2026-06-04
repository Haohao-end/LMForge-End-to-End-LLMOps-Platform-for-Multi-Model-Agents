from __future__ import annotations

from internal.core.agent.entities.artifact_policy_entity import ArtifactPolicy


def test_artifact_policy_should_infer_default_filenames_without_explicit_name():
    prospectus_query = (
        "生成 SpaceX IPO 招股说明书 txt 文件，要求输出可下载 .txt 附件。"
        "内容包含：封面摘要、业务概览、风险因素、MD&A、募集资金用途、法律声明。"
    )
    travel_query = (
        "请输出可下载的 Markdown 附件。内容包含：行程总览、每日安排、住宿建议、交通建议、预算。"
        "我第一次去北京，只有 2 天时间，同行有长辈。"
    )

    assert (
        ArtifactPolicy.resolve_artifact_filename(prospectus_query, allow_default_filename=True)
        == "SpaceX_IPO_Prospectus_Draft.txt"
    )
    assert ArtifactPolicy.resolve_artifact_filename(travel_query, allow_default_filename=True) == "Travel_Plan.md"


def test_artifact_policy_should_strip_generic_plain_text_boilerplate():
    text = (
        "说明：当前对话环境暂不直接支持自动生成可下载附件，但以下为您提供完整、可直接复制保存的 .txt 文件内容。\n\n"
        "================================================================================\n"
        "SPACE EXPLORATION TECHNOLOGIES CORP.\n"
        "PROSPECTUS DRAFT\n"
        "================================================================================\n\n"
        "PROSPECTUS SUMMARY\n"
        "The Company ...\n"
    )

    cleaned = ArtifactPolicy.strip_plain_text_artifact_preamble(text)

    assert "暂不直接支持自动生成可下载附件" not in cleaned
    assert cleaned.startswith("================================================================================")
    assert "SPACE EXPLORATION TECHNOLOGIES CORP." in cleaned


def test_artifact_policy_should_extract_write_file_payload_from_generated_artifacts():
    text = """<generated_artifacts>
<artifact id="spacex_prospectus" title="SpaceX IPO Prospectus Draft" commit_message="Generate SpaceX IPO Prospectus Draft in txt format">

SPACE EXPLORATION TECHNOLOGIES CORP.
IPO招股说明书草案
</artifact>
</generated_artifacts>"""

    payload = ArtifactPolicy.extract_write_file_payload(text)

    assert payload is not None
    path, content = payload
    assert path == "SpaceX_IPO_Prospectus_Draft.txt"
    assert "SPACE EXPLORATION TECHNOLOGIES CORP." in content
    assert "IPO招股说明书草案" in content
