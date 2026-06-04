from internal.core.agent.entities.tool_policy_entity import (
    DATASET_RETRIEVAL_TOOL_NAME,
    ToolPolicy,
)


def test_tool_policy_should_expose_default_shared_strategy():
    policy = ToolPolicy()

    assert policy.dataset_retrieval_tool_name == DATASET_RETRIEVAL_TOOL_NAME
    assert policy.resolve_tool_name("recall_dataset") == DATASET_RETRIEVAL_TOOL_NAME
    assert policy.resolve_tool_name("dataset_retrieval") == DATASET_RETRIEVAL_TOOL_NAME
    assert policy.is_hard_fail_tool("qwen_image_edit")
    assert policy.is_hard_fail_tool("qwen_image_edit_2509")
    assert policy.is_image_result_tool("qwen_image_text_to_image")


def test_tool_policy_should_support_custom_overrides():
    policy = ToolPolicy(
        hard_fail_tool_names=("custom_hard_fail_tool",),
        tool_alias_synonyms={"custom_alias": "custom_tool"},
        image_result_tool_names=("custom_image_tool",),
    )

    assert policy.resolve_tool_name("custom_alias") == "custom_tool"
    assert policy.is_hard_fail_tool("custom_hard_fail_tool")
    assert policy.is_image_result_tool("custom_image_tool")
    assert not policy.is_hard_fail_tool("qwen_image_edit")
    assert not policy.is_image_result_tool("qwen_image_text_to_image")
