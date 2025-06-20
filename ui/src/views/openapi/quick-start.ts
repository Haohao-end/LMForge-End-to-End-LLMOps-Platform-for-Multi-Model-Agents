export const blockApiShell = `curl --location --request POST 'https://localhost:5000/openapi/chat \\
--header 'Authorization: Bearer pat_OYDacMzM3WyOWV3Dtj2bHRMymzxP****' \\
--header 'Content-Type: application/json' \\
--data-raw '{
    "app_id": "734829333445931****",
    "end_user_id": "123456789",
    "conversation_id": "123456789",
    "stream": false,
    "query": "广州今天的天气怎样"
}'`

export const blockApiOutput = `{
    "code": "success",
    "data": {
        "agent_thoughts": [
            {
                "created_at": 0,
                "event": "long_term_memory_recall",
                "id": "bb3af322-ee05-4914-b678-f9ab0c1100f2",
                "latency": 0,
                "observation": "",
                "thought": "",
                "tool": "",
                "tool_input": {}
            },
            {
                "created_at": 0,
                "event": "agent_thought",
                "id": "3772f55f-f74d-4226-ac6b-262f12e638b3",
                "latency": 10.352535700018052,
                "observation": "",
                "thought": "[{\\"name\\": \\"google_serper\\", \\"args\\": {\\"query\\": \\"2024\\年\\北\\京\\半\\程\\马\\拉\\松 \\前3\\名\\成\\绩\\"}, \\"id\\": \\"chatcmpl-6n0EI9LEUaiONA3rzlNOzLKRI5mFj\\", \\"type\\": \\"tool_call\\"}]",
                "tool": "",
                "tool_input": {}
            },
            {
                "created_at": 0,
                "event": "agent_action",
                "id": "8ccda267-b8b9-407a-b331-e53e13413777",
                "latency": 1.2946343999938108,
                "observation": "\\"\\经\\过\\激\\烈\\角\\逐\\，\\男\\子\\组\\方\\面\\，\\中\\国\\选\\手\\何\\杰\\以1\\小\\时03\\分44\\秒\\的\\成\\绩\\夺\\得\\冠\\军\\，\\埃\\塞\\俄\\比\\亚\\选\\手DEJENE HAILU BIKILA\\以\\及\\来\\自\\肯\\尼\\亚\\的Robert Keter\\和WILLY MNANGAT\\三\\人\\以1\\小\\时03\\分45\\秒\\的\\成\\绩\\并\\列\\获\\得\\亚\\军\\，\\中\\国\\选\\手\\李\\春\\晖\\则\\以1\\小\\时06\\分58\\秒\\的\\成\\绩\\获\\得\\季\\军\\。\\"",
                "thought": "",
                "tool": "google_serper",
                "tool_input": {
                    "query": "2024年北京半程马拉松 前3名成绩"
                }
            },
            {
                "created_at": 0,
                "event": "agent_message",
                "id": "2838d7e4-a368-4340-88d4-009245d895a1",
                "latency": 4.272923699987587,
                "observation": "",
                "thought": "在2024年北京半程马拉松中，前3名的成绩如下：\\n\\n1. 男子组冠军：来自中国的选手，成绩为1小时3分44秒。\\n2. 男子组亚军：来自埃塞俄比亚的Dejene Hailu Bikila，成绩为1小时3分45秒。\\n3. 男子组季军：来自肯尼亚的Robert Keter，成绩为1小时3分46秒。\\n\\n女子组方面，冠军是中国选手李春霞，成绩为1小时6分58秒。",
                "tool": "",
                "tool_input": {}
            },
            {
                "created_at": 0,
                "event": "agent_end",
                "id": "1b963062-8623-4e6e-a65e-16249d1c1ee8",
                "latency": 0,
                "observation": "",
                "thought": "",
                "tool": "",
                "tool_input": {}
            }
        ],
        "answer": "在2024年北京半程马拉松中，前3名的成绩如下：\\n\\n1. 男子组冠军：来自中国的选手，成绩为1小时3分44秒。\\n2. 男子组亚军：来自埃塞俄比亚的Dejene Hailu Bikila，成绩为1小时3分45秒。\\n3. 男子组季军：来自肯尼亚的Robert Keter，成绩为1小时3分46秒。\\n\\n女子组方面，冠军是中国选手李春霞，成绩为1小时6分58秒。",
        "conversation_id": "11356d51-7047-4668-9a7a-5fb6eb27e032",
        "end_user_id": "c63840ec-3362-4525-8fb3-eb99fded09c2",
        "id": "9ada9487-2274-4003-820b-b57997229ac8",
        "latency": 15.92009379999945,
        "query": "帮我看下2024年北京半程马拉松的前3名成绩是多少",
        "total_token_count": 0
    },
    "message": ""
}`

export const streamApiShell = `curl --location --request POST 'https://localhost:5000/openapi/chat \\
--header 'Authorization: Bearer pat_OYDacMzM3WyOWV3Dtj2bHRMymzxP****' \\
--header 'Content-Type: application/json' \\
--data-raw '{
    "app_id": "734829333445931****",
    "end_user_id": "123456789",
    "conversation_id": "123456789",
    "stream": true,
    "query": "广州今天的天气怎样"
}'`

export const streamApiOutput = `event: long_term_memory_recall
data:{"event": "long_term_memory_recall", "thought": "", "observation": "", "tool": "", "tool_input": {}, "answer": "", "latency": 0, "id": "8bfc7813-6a0b-4e40-8505-65a5d9ddeadc", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}

event: agent_thought
data:{"event": "agent_thought", "thought": "[{\\"name\\": \\"google_serper\\", \\"args\\": {\\"query\\": \\"2024\\\u5e74\\\u5317\\\u4eac\\\u534a\\\u7a0b\\\u9a6c\\\u62c9\\\u677e \\\u524d3\\\u540d \\\u6210\\\u7ee9\\"}, \\"id\\": \\"chatcmpl-ZkqMmN4decBOYyCcxYMOSe7LjYI1K\\", \\"type\\": \\"tool_call\\"}]", "observation": "", "tool": "", "tool_input": {}, "answer": "", "latency": 7.987706799991429, "id": "234b3b12-4b29-416d-847f-0c23f21715d3", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}

event: agent_action
data:{"event": "agent_action", "thought": "", "observation": "\\"\\\u7ecf\\\u8fc7\\\u6fc0\\\u70c8\\\u89d2\\\u9010\\\uff0c\\\u7537\\\u5b50\\\u7ec4\\\u65b9\\\u9762\\\uff0c\\\u4e2d\\\u56fd\\\u9009\\\u624b\\\u4f55\\\u6770\\\u4ee51\\\u5c0f\\\u65f603\\\u520644\\\u79d2\\\u7684\\\u6210\\\u7ee9\\\u593a\\\u5f97\\\u51a0\\\u519b\\\uff0c\\\u57c3\\\u585e\\\u4fc4\\\u6bd4\\\u4e9a\\\u9009\\\u624bDEJENE HAILU BIKILA\\\u4ee5\\\u53ca\\\u6765\\\u81ea\\\u80af\\\u5c3c\\\u4e9a\\\u7684Robert Keter\\\u548cWILLY MNANGAT\\\u4e09\\\u4eba\\\u4ee51\\\u5c0f\\\u65f603\\\u520645\\\u79d2\\\u7684\\\u6210\\\u7ee9\\\u5e76\\\u5217\\\u83b7\\\u5f97\\\u4e9a\\\u519b\\\uff0c\\\u4e2d\\\u56fd\\\u9009\\\u624b\\\u674e\\\u6625\\\u6656\\\u5219\\\u4ee51\\\u5c0f\\\u65f606\\\u520658\\\u79d2\\\u7684\\\u6210\\\u7ee9\\\u83b7\\\u5f97\\\u5b63\\\u519b\\\u3002\\"", "tool": "google_serper", "tool_input": {"query": "2024\u5e74\u5317\u4eac\u534a\u7a0b\u9a6c\u62c9\u677e \u524d3\u540d \u6210\u7ee9"}, "answer": "", "latency": 1.018759400001727, "id": "42aa6d10-b9f0-46b8-84d4-c73753d2d716", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}

event: ping
data:{"event": "ping", "thought": "", "observation": "", "tool": "", "tool_input": {}, "answer": "", "latency": 0, "id": "18f79eab-9025-4b1b-94a3-75ea42fa7029", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}

event: agent_message
data:{"event": "agent_message", "thought": "202", "observation": "", "tool": "", "tool_input": {}, "answer": "202", "latency": 5.723647899983916, "id": "0d290337-3b10-4d2a-88c4-72891ca8ebd4", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}

event: agent_message
data:{"event": "agent_message", "thought": "4", "observation": "", "tool": "", "tool_input": {}, "answer": "4", "latency": 5.72700110002188, "id": "0d290337-3b10-4d2a-88c4-72891ca8ebd4", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}

event: agent_message
data:{"event": "agent_message", "thought": "\u5e74", "observation": "", "tool": "", "tool_input": {}, "answer": "\u5e74", "latency": 5.735950900008902, "id": "0d290337-3b10-4d2a-88c4-72891ca8ebd4", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}

event: agent_message
data:{"event": "agent_message", "thought": "\u3002", "observation": "", "tool": "", "tool_input": {}, "answer": "\u3002", "latency": 6.779141300008632, "id": "0d290337-3b10-4d2a-88c4-72891ca8ebd4", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}

event: agent_message
data:{"event": "agent_message", "thought": "", "observation": "", "tool": "", "tool_input": {}, "answer": "", "latency": 6.779683900007512, "id": "0d290337-3b10-4d2a-88c4-72891ca8ebd4", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}

event: agent_end
data:{"event": "agent_end", "thought": "", "observation": "", "tool": "", "tool_input": {}, "answer": "", "latency": 0, "id": "020deae7-6307-4e39-8378-bfdaa11e0f0d", "end_user_id": "d010ddef-181d-4c04-9d29-edd60c9c0da8", "conversation_id": "76cf52b8-36b7-4fd5-af8b-65547991f84a", "message_id": "ed221e86-4d8f-43b0-8d35-a70fbbc7b0b3", "task_id": "03042ead-23d6-42c6-a5c9-caac416bb80c"}
`
