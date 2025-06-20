<script setup lang="ts">
import { v4 } from 'uuid'
import { markRaw, onMounted, ref } from 'vue'
import moment from 'moment/moment'
import { useRoute } from 'vue-router'
import { ConnectionMode, Panel, useVueFlow, VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import dagre from 'dagre'
import { cloneDeep } from 'lodash'
import {
  useCancelPublishWorkflow,
  useGetDraftGraph,
  useGetWorkflow,
  usePublishWorkflow,
  useUpdateDraftGraph,
} from '@/hooks/use-workflow'
import StartNode from './components/nodes/StartNode.vue'
import LlmNode from './components/nodes/LLMNode.vue'
import DatasetRetrievalNode from './components/nodes/DatasetRetrievalNode.vue'
import CodeNode from './components/nodes/CodeNode.vue'
import HttpRequestNode from './components/nodes/HttpRequestNode.vue'
import ToolNode from './components/nodes/ToolNode.vue'
import TemplateTransformNode from './components/nodes/TemplateTransformNode.vue'
import EndNode from './components/nodes/EndNode.vue'
import DebugModal from './components/DebugModal.vue'
import StartNodeInfo from './components/infos/StartNodeInfo.vue'
import LlmNodeInfo from './components/infos/LLMNodeInfo.vue'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/minimap/dist/style.css'
import { Message } from '@arco-design/web-vue'
import { generateRandomString } from '@/utils/helper'
import TemplateTransformNodeInfo from '@/views/space/workflows/components/infos/TemplateTransformNodeInfo.vue'
import CodeNodeInfo from '@/views/space/workflows/components/infos/CodeNodeInfo.vue'
import HttpRequestNodeInfo from '@/views/space/workflows/components/infos/HttpRequestNodeInfo.vue'
import DatasetRetrievalNodeInfo from '@/views/space/workflows/components/infos/DatasetRetrievalNodeInfo.vue'
import ToolNodeInfo from '@/views/space/workflows/components/infos/ToolNodeInfo.vue'
import EndNodeInfo from '@/views/space/workflows/components/infos/EndNodeInfo.vue'

// 1.定义页面所需数据
const route = useRoute()
const instance = ref<any>(null)
const zoomLevel = ref<number>(1)
const zoomOptions = [
  { label: '200%', value: 2 },
  { label: '100%', value: 1 },
  { label: '75%', value: 0.75 },
  { label: '50%', value: 0.5 },
  { label: '25%', value: 0.25 },
]
const NOTE_TYPES = {
  start: markRaw(StartNode),
  llm: markRaw(LlmNode),
  tool: markRaw(ToolNode),
  dataset_retrieval: markRaw(DatasetRetrievalNode),
  template_transform: markRaw(TemplateTransformNode),
  http_request: markRaw(HttpRequestNode),
  code: markRaw(CodeNode),
  end: markRaw(EndNode),
}
const NODE_DATA_MAP: Record<string, any> = {
  start: {
    title: '开始节点',
    description: '工作流的起点节点，支持定义工作流的起点输入等信息',
    inputs: [],
  },
  llm: {
    title: '大语言模型',
    description: '调用大语言模型，根据输入参数和提示词生成回复。',
    prompt: '',
    model_config: {
      provider: 'openai',
      model: 'gpt-4o-mini',
      parameters: {
        frequency_penalty: 0.2,
        max_tokens: 8192,
        presence_penalty: 0.2,
        temperature: 0.5,
        top_p: 0.85,
      },
    },
    inputs: [],
    outputs: [{ name: 'output', type: 'string', value: { type: 'generated', content: '' } }],
  },
  tool: {
    title: '扩展插件',
    description: '调用插件广场或自定义API插件，支持能力扩展和复用',
    tool_type: '',
    provider_id: '',
    tool_id: '',
    params: {},
    inputs: [],
    outputs: [{ name: 'text', type: 'string', value: { type: 'generated', content: '' } }],
    meta: {
      type: 'api_tool',
      provider: { id: '', name: '', label: '', icon: '', description: '' },
      tool: { id: '', name: '', label: '', description: '', params: {} },
    },
  },
  dataset_retrieval: {
    title: '知识库检索',
    description: '根据输入的参数，在选定的知识库中检索相关片段并召回，返回切片列表',
    dataset_ids: [],
    retrieval_config: {
      retrieval_strategy: 'semantic',
      k: 4,
      score: 0,
    },
    inputs: [
      {
        name: 'query',
        type: 'string',
        value: { type: 'ref', content: { ref_node_id: '', ref_var_name: '' } },
      },
    ],
    outputs: [
      { name: 'combine_documents', type: 'string', value: { type: 'generated', content: '' } },
    ],
    meta: { datasets: [] },
  },
  template_transform: {
    title: '模板转换',
    description: '对多个字符串变量的格式进行处理',
    template: '',
    inputs: [],
    outputs: [{ name: 'output', type: 'string', value: { type: 'generated', content: '' } }],
  },
  http_request: {
    title: 'HTTP请求',
    description: '配置外部API服务，并发起请求。',
    url: '',
    method: 'get',
    inputs: [],
    outputs: [
      { name: 'status_code', type: 'int', value: { type: 'generated', content: 0 } },
      { name: 'text', type: 'string', value: { type: 'generated', content: '' } },
    ],
  },
  code: {
    title: 'Python代码执行',
    description: '编写代码，处理输入输出变量来生成返回值',
    code: '',
    inputs: [],
    outputs: [],
  },
  end: {
    title: '结束节点',
    description: '工作流的结束节点，支持定义工作流最终输出的变量等信息',
    outputs: [],
  },
}
const selectedNode = ref<any>(null) // 选择的节点
const isInitializing = ref(true) // 数据是否初始化
const isDebug = ref(false) // 是否处于调试状态
const nodeInfoVisible = ref(false) // 节点信息是否显示
const {
  onPaneReady, // 面板加载完毕事件
  onViewportChange, // 视口变化回调函数
  onConnect, // 边连接回调函数
  onPaneClick, // 工作流面板点击事件
  onNodeClick, // 节点点击事件
  onEdgeClick, // 边点击事件
  onNodeDragStop, // 节点拖动停止回调函数
  findNode, // 根据id查找节点
  nodes: allNodes, // 所有节点
} = useVueFlow()
const { loading: getWorkflowLoading, workflow, loadWorkflow } = useGetWorkflow()
const {
  loading: updateDraftGraphLoading,
  handleUpdateDraftGraph,
  convertGraphToReq,
} = useUpdateDraftGraph()
const { nodes, edges, loadDraftGraph } = useGetDraftGraph()
const { loading: publishWorkflowLoading, handlePublishWorkflow } = usePublishWorkflow()
const { handleCancelPublish } = useCancelPublishWorkflow()

// 2.定义自适应布局处理器
const autoLayout = () => {
  // 2.1 创建dagre图结构
  const dagreGraph = new dagre.graphlib.Graph()

  // 2.2 设置布局参数
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({
    rankdir: 'LR', // 纵向布局
    align: 'UL', // 左上对齐
    nodesep: 80, // 节点间距
    ranksep: 60, // 层次间距
    edgesep: 10, // 边间距
  })

  // 2.3 深度拷贝nodes和edges对应的数据，避免影响元数据
  const cloneNodes = cloneDeep(nodes.value)
  const cloneEdges = cloneDeep(edges.value)

  // 2.4 将节点添加到图中
  cloneNodes.forEach((node: any) => {
    dagreGraph.setNode(node.id, { width: node.dimensions.width, height: node.dimensions.height })
  })

  // 2.5 将边添加到图中
  cloneEdges.forEach((edge: any) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  // 2.6 运行布局算法
  dagre.layout(dagreGraph)

  // 2.7 根据布局结果更新工作流的图结构布局
  nodes.value = cloneNodes.map((node: any) => {
    const { x, y } = dagreGraph.node(node.id)
    return {
      ...node,
      position: { x, y },
    }
  })
}

// 3.定义添加节点处理器
const addNode = (node_type: string) => {
  // 3.1 检测点击的类型是否为start/end，一个工作流中只允许有一个start和一个node
  if (node_type === 'start') {
    // 3.2 判断在图中是否存在开始节点
    if (allNodes.value.some((node) => node.type === 'start')) {
      Message.error('工作流中只允许有一个开始节点')
      return
    }
  } else if (node_type === 'end') {
    // 3.3 判断在图中是否存在结束节点
    if (allNodes.value.some((node) => node.type === 'end')) {
      Message.error('工作流中只允许有一个结束节点')
      return
    }
  }

  // 3.4 计算所有节点的平均位置
  const node_count = allNodes.value.length
  const total = allNodes.value.reduce(
    (acc, item) => {
      acc.xSum += item.position.x
      acc.ySum += item.position.y
      return acc
    },
    { xSum: 0, ySum: 0 },
  )
  const xAverage = node_count > 0 ? total.xSum / node_count : 0
  const yAverage = node_count > 0 ? total.ySum / node_count : 0

  // 3.5 提取节点数据的默认值
  const node_data = NODE_DATA_MAP[node_type]

  // 3.6 添加节点数据
  nodes.value.push({
    id: v4(),
    type: node_type,
    position: { x: xAverage, y: yAverage },
    data: {
      ...node_data,
      title: `${node_data.title}_${generateRandomString(5)}`,
    },
  })
}

// 定义监听工作流变化事件（涵盖节点+边）
const onChange = () => {
  // 检测是否初始化，如果是则直接中断程序
  if (isInitializing.value) return

  // 如果不是则发起更新图草稿配置
  handleUpdateDraftGraph(
    String(route.params?.workflow_id ?? ''),
    convertGraphToReq(nodes.value, edges.value),
  )
}

// 定义节点更新事件
const onUpdateNode = (node_data: Record<string, any>) => {
  // 获取该节点对应的索引
  const idx = nodes.value.findIndex((item: any) => item.id === node_data.id)

  // 检测是否存在数据，如果存在则更新
  if (idx !== -1) {
    nodes.value[idx].data = {
      ...nodes.value[idx].data,
      ...node_data,
    }
  }

  // 调用API发起更新请求，由于字典嵌套比较深@update有可能无法主动监听
  handleUpdateDraftGraph(
    String(route.params?.workflow_id ?? ''),
    convertGraphToReq(nodes.value, edges.value),
    true,
  )
}

// 节点链接hooks
onConnect((connection) => {
  // 获取节点和目标的节点id
  const { source, target } = connection

  // 检查是否连接统一节点
  if (source === target) {
    Message.error('不能将节点连接到本身')
    return
  }

  // 检查节点和目标节点是否已经存在链接
  const isAlreadyConnected = edges.value.some((edge: any) => {
    return (
      (edge.source === source && edge.target === target) ||
      (edge.source === target && edge.target === source)
    )
  })

  // 如果已经连接，则提示用户并阻止连接
  if (isAlreadyConnected) {
    Message.error('这两个节点已有连接，无需重复添加')
    return
  }

  // 获取边的起点和终点类型
  const source_node = findNode(source)
  const target_node = findNode(target)

  // 将数据添加到edges
  edges.value.push({
    ...connection,
    id: v4(),
    source_type: source_node?.type,
    target_type: target_node?.type,
    animated: true,
    style: { strokeWidth: 2, stroke: '#9ca3af' },
  })
})

// 工作流面板点击hooks
onPaneClick(() => {
  isDebug.value = false
  selectedNode.value = null
})

// 工作流Edge边点击hooks
onEdgeClick(() => {
  isDebug.value = false
  selectedNode.value = null
})

// 工作流Node点击hooks
onNodeClick((nodeMouseEvent) => {
  // 限制每个节点只能点击一次，点击的时候将节点的数据赋值给selectedNode
  if (!selectedNode.value || selectedNode.value?.id !== nodeMouseEvent.node.id) {
    selectedNode.value = nodeMouseEvent.node
    nodeInfoVisible.value = true
  }

  isDebug.value = false
})

// 工作流节点拖动停止hooks
onNodeDragStop(() => {
  handleUpdateDraftGraph(
    String(route.params?.workflow_id ?? ''),
    convertGraphToReq(nodes.value, edges.value),
    false,
  )
})

// 工作流面板加载完毕后的回调函数
onPaneReady((vueFlowInstance) => {
  vueFlowInstance.fitView()
  instance.value = vueFlowInstance
})

// 定义视口变化回调函数
onViewportChange((viewportTransform) => {
  zoomLevel.value = viewportTransform.zoom
})

// 页面DOM挂载完毕后加载数据
onMounted(async () => {
  const workflow_id = String(route.params?.workflow_id ?? '')
  await loadWorkflow(workflow_id)
  await loadDraftGraph(workflow_id)
  isInitializing.value = false
})
</script>

<template>
  <!-- 外部容器 -->
  <div class="min-h-screen flex flex-col h-full overflow-hidden relative">
    <!-- 顶部Header -->
    <div
      class="h-[77px] flex-shrink-0 bg-white p-4 flex items-center justify-between relative border-b"
    >
      <!-- 左侧工作流信息 -->
      <div class="flex items-center gap-2">
        <!-- 回退按钮 -->
        <router-link :to="{ name: 'space-workflows-list' }">
          <a-button size="mini">
            <template #icon>
              <icon-left />
            </template>
          </a-button>
        </router-link>
        <!-- 工作流容器 -->
        <div class="flex items-center gap-3">
          <!-- 工作流图标 -->
          <a-avatar :size="40" shape="square" class="rounded-lg" :image-url="workflow.icon" />
          <!-- 工作流信息 -->
          <div class="flex flex-col justify-between h-[40px]">
            <a-skeleton-line v-if="getWorkflowLoading" :widths="[100]" />
            <div v-else class="text-gray-700 font-bold">{{ workflow.name }}</div>
            <div v-if="getWorkflowLoading" class="flex items-center gap-2">
              <a-skeleton-line :widths="[60]" :line-height="18" />
              <a-skeleton-line :widths="[60]" :line-height="18" />
              <a-skeleton-line :widths="[60]" :line-height="18" />
            </div>
            <div v-else class="flex items-center gap-2">
              <div class="max-w-[160px] line-clamp-1 text-xs text-gray-500">
                {{ workflow.description }}
              </div>
              <div class="flex items-center h-[18px] text-xs text-gray-500">
                <icon-schedule />
                {{ workflow.status === 'draft' ? '草稿' : '已发布' }}
              </div>
              <a-tag size="small" class="rounded h-[18px] leading-[18px] bg-gray-200 text-gray-500">
                已自动保存 {{ moment(workflow.updated_at * 1000).format('HH:mm:ss') }}
              </a-tag>
            </div>
          </div>
        </div>
      </div>
      <!-- 右侧操作按钮 -->
      <div class="">
        <a-space :size="12">
          <a-button-group>
            <a-button
              :disabled="!workflow.is_debug_passed"
              :loading="publishWorkflowLoading"
              type="primary"
              class="!rounded-tl-lg !rounded-bl-lg"
              @click="() => handlePublishWorkflow(String(workflow.id))"
            >
              更新发布
            </a-button>
            <a-dropdown position="br">
              <a-button
                :disabled="workflow.status !== 'published'"
                type="primary"
                class="!rounded-tr-lg !rounded-br-lg !w-5"
              >
                <template #icon>
                  <icon-down />
                </template>
              </a-button>
              <template #content>
                <a-doption
                  :disabled="workflow.status !== 'published'"
                  class="!text-red-700"
                  @click="() => handleCancelPublish(String(workflow.id))"
                >
                  取消发布
                </a-doption>
              </template>
            </a-dropdown>
          </a-button-group>
        </a-space>
      </div>
    </div>
    <!-- 中间编排画布 -->
    <div class="flex-1">
      <vue-flow
        :min-zoom="0.25"
        :max-zoom="2"
        :nodes-connectable="true"
        :connection-mode="ConnectionMode.Strict"
        :connection-line-options="{ style: { strokeWidth: 2, stroke: '#9ca3af' } }"
        :node-types="NOTE_TYPES"
        v-model:nodes="nodes"
        v-model:edges="edges"
        @update:nodes="onChange"
        @update:edges="onChange"
      >
        <!-- 工作流背景 -->
        <background />
        <!-- 迷你地图 -->
        <mini-map
          class="rounded-xl border border-gray-300 overflow-hidden !left-0 !right-auto"
          :width="160"
          :height="96"
          pannable
          zoomable
        />
        <!-- 使用默认插槽添加工具菜单 -->
        <panel position="bottom-center">
          <div class="p-[5px] bg-white rounded-xl border z-50">
            <a-space :size="8">
              <template #split>
                <a-divider direction="vertical" class="m-0" />
              </template>
              <!-- 添加节点 -->
              <a-trigger position="top" :popup-translate="[0, -16]">
                <a-button type="primary" size="small" class="rounded-lg px-2">
                  <template #icon>
                    <icon-plus-circle-fill />
                  </template>
                  节点
                </a-button>
                <template #content>
                  <div
                    class="bg-white borer border-gray-200 w-[240px] shadow rounded-xl overflow-hidden py-2"
                  >
                    <!-- 开始节点 -->
                    <div
                      class="flex flex-col px-3 py-2 gap-2 cursor-pointer hover:bg-gray-50"
                      @click="() => addNode('start')"
                    >
                      <!-- 节点名称 -->
                      <div class="flex items-center gap-2">
                        <a-avatar shape="square" :size="24" class="bg-blue-700 rounded-lg">
                          <icon-home />
                        </a-avatar>
                        <div class="text-gray-700 font-semibold">开始节点</div>
                      </div>
                      <!-- 节点描述 -->
                      <div class="text-gray-500 text-xs">
                        工作流的起始节点，支持定义工作流的起点输入等信息。
                      </div>
                    </div>
                    <!-- 大语言模型节点 -->
                    <div
                      class="flex flex-col px-3 py-2 gap-2 cursor-pointer hover:bg-gray-50"
                      @click="() => addNode('llm')"
                    >
                      <!-- 节点名称 -->
                      <div class="flex items-center gap-2">
                        <a-avatar shape="square" :size="24" class="bg-sky-500 rounded-lg">
                          <icon-language />
                        </a-avatar>
                        <div class="text-gray-700 font-semibold">大语言模型</div>
                      </div>
                      <!-- 节点描述 -->
                      <div class="text-gray-500 text-xs">
                        调用大语言模型，根据输入参数和提示词生成回复
                      </div>
                    </div>
                    <!-- 扩展插件 -->
                    <div
                      class="flex flex-col px-3 py-2 gap-2 cursor-pointer hover:bg-gray-50"
                      @click="() => addNode('tool')"
                    >
                      <!-- 节点名称 -->
                      <div class="flex items-center gap-2">
                        <a-avatar shape="square" :size="24" class="bg-orange-500 rounded-lg">
                          <icon-tool />
                        </a-avatar>
                        <div class="text-gray-700 font-semibold">扩展插件</div>
                      </div>
                      <!-- 节点描述 -->
                      <div class="text-gray-500 text-xs">
                        添加插件广场内或自定义API插件，支持能力扩展和复用。
                      </div>
                    </div>
                    <!-- 知识库检索 -->
                    <div
                      class="flex flex-col px-3 py-2 gap-2 cursor-pointer hover:bg-gray-50"
                      @click="() => addNode('dataset_retrieval')"
                    >
                      <!-- 节点名称 -->
                      <div class="flex items-center gap-2">
                        <a-avatar shape="square" :size="24" class="bg-violet-500 rounded-lg">
                          <icon-storage />
                        </a-avatar>
                        <div class="text-gray-700 font-semibold">知识库检索</div>
                      </div>
                      <!-- 节点描述 -->
                      <div class="text-gray-500 text-xs">
                        根据输入的参数，在选定的知识库中检索相关片段并召回，返回切片列表。
                      </div>
                    </div>
                    <!-- 模板转换 -->
                    <div
                      class="flex flex-col px-3 py-2 gap-2 cursor-pointer hover:bg-gray-50"
                      @click="() => addNode('template_transform')"
                    >
                      <!-- 节点名称 -->
                      <div class="flex items-center gap-2">
                        <a-avatar shape="square" :size="24" class="bg-emerald-400 rounded-lg">
                          <icon-branch />
                        </a-avatar>
                        <div class="text-gray-700 font-semibold">模板转换</div>
                      </div>
                      <!-- 节点描述 -->
                      <div class="text-gray-500 text-xs">对多个字符串变量的格式进行处理。</div>
                    </div>
                    <!-- HTTP请求 -->
                    <div
                      class="flex flex-col px-3 py-2 gap-2 cursor-pointer hover:bg-gray-50"
                      @click="() => addNode('http_request')"
                    >
                      <!-- 节点名称 -->
                      <div class="flex items-center gap-2">
                        <a-avatar shape="square" :size="24" class="bg-rose-500 rounded-lg">
                          <icon-link />
                        </a-avatar>
                        <div class="text-gray-700 font-semibold">HTTP请求</div>
                      </div>
                      <!-- 节点描述 -->
                      <div class="text-gray-500 text-xs">配置外部API服务，并发起请求。</div>
                    </div>
                    <!-- Python代码执行 -->
                    <div
                      class="flex flex-col px-3 py-2 gap-2 cursor-pointer hover:bg-gray-50"
                      @click="() => addNode('code')"
                    >
                      <!-- 节点名称 -->
                      <div class="flex items-center gap-2">
                        <a-avatar shape="square" :size="24" class="bg-cyan-500 rounded-lg">
                          <icon-code />
                        </a-avatar>
                        <div class="text-gray-700 font-semibold">Python代码执行</div>
                      </div>
                      <!-- 节点描述 -->
                      <div class="text-gray-500 text-xs">
                        编写代码处理输入输出变量来生成返回值。
                      </div>
                    </div>
                    <!-- 结束节点 -->
                    <div
                      class="flex flex-col px-3 py-2 gap-2 cursor-pointer hover:bg-gray-50"
                      @click="() => addNode('end')"
                    >
                      <!-- 节点名称 -->
                      <div class="flex items-center gap-2">
                        <a-avatar shape="square" :size="24" class="bg-red-700 rounded-lg">
                          <icon-filter />
                        </a-avatar>
                        <div class="text-gray-700 font-semibold">结束节点</div>
                      </div>
                      <!-- 节点描述 -->
                      <div class="text-gray-500 text-xs">
                        工作流的结束节点，支持定义工作流最终输出的变量等信息。
                      </div>
                    </div>
                  </div>
                </template>
              </a-trigger>
              <!-- 自适应布局&视口大小 -->
              <div class="flex items-center gap-3">
                <a-tooltip content="自适应布局">
                  <a-button
                    size="small"
                    type="text"
                    class="!text-gray-700 rounded-lg"
                    @click="() => autoLayout()"
                  >
                    <template #icon>
                      <icon-apps />
                    </template>
                  </a-button>
                </a-tooltip>
                <a-dropdown
                  trigger="hover"
                  @select="
                    (value: any) => {
                      // 调整视口大小并更新视口等级
                      zoomLevel = Number(value)
                      instance.zoomTo(value)
                    }
                  "
                >
                  <a-button size="small" class="!text-gray-700 px-2 rounded-lg gap-1 w-[80px]">
                    {{ (zoomLevel * 100).toFixed(0) }}%
                    <icon-down />
                  </a-button>
                  <template #content>
                    <a-doption v-for="zoom in zoomOptions" :key="zoom.value" :value="zoom.value">
                      {{ zoom.label }}
                    </a-doption>
                  </template>
                </a-dropdown>
              </div>
              <!-- 调试与预览 -->
              <a-button
                type="text"
                size="small"
                class="px-2 rounded-lg"
                @click="
                  () => {
                    // 清空当前选中节点并设置调试模式
                    selectedNode = null
                    isDebug = true
                  }
                "
              >
                <template #icon>
                  <icon-play-arrow />
                </template>
                调试
              </a-button>
            </a-space>
          </div>
        </panel>
        <!-- 调试与预览窗口 -->
        <debug-modal
          :workflow_id="String(route.params?.workflow_id ?? '')"
          v-model:visible="isDebug"
        />
        <!-- 节点信息容器 -->
        <start-node-info
          v-if="selectedNode && selectedNode?.type === 'start'"
          :loading="updateDraftGraphLoading"
          :node="selectedNode"
          v-model:visible="nodeInfoVisible"
          @update-node="onUpdateNode"
        />
        <llm-node-info
          v-if="selectedNode && selectedNode?.type === 'llm'"
          :loading="updateDraftGraphLoading"
          :node="selectedNode"
          v-model:visible="nodeInfoVisible"
          @update-node="onUpdateNode"
        />
        <template-transform-node-info
          v-if="selectedNode && selectedNode?.type === 'template_transform'"
          :loading="updateDraftGraphLoading"
          :node="selectedNode"
          v-model:visible="nodeInfoVisible"
          @update-node="onUpdateNode"
        />
        <code-node-info
          v-if="selectedNode && selectedNode?.type === 'code'"
          :loading="updateDraftGraphLoading"
          :node="selectedNode"
          v-model:visible="nodeInfoVisible"
          @update-node="onUpdateNode"
        />
        <http-request-node-info
          v-if="selectedNode && selectedNode?.type === 'http_request'"
          :loading="updateDraftGraphLoading"
          :node="selectedNode"
          v-model:visible="nodeInfoVisible"
          @update-node="onUpdateNode"
        />
        <dataset-retrieval-node-info
          v-if="selectedNode && selectedNode?.type === 'dataset_retrieval'"
          :loading="updateDraftGraphLoading"
          :node="selectedNode"
          v-model:visible="nodeInfoVisible"
          @update-node="onUpdateNode"
        />
        <tool-node-info
          v-if="selectedNode && selectedNode?.type === 'tool'"
          :loading="updateDraftGraphLoading"
          :node="selectedNode"
          v-model:visible="nodeInfoVisible"
          @update-node="onUpdateNode"
        />
        <end-node-info
          v-if="selectedNode && selectedNode?.type === 'end'"
          :loading="updateDraftGraphLoading"
          :node="selectedNode"
          v-model:visible="nodeInfoVisible"
          @update-node="onUpdateNode"
        />
      </vue-flow>
    </div>
  </div>
</template>

<style>
.selected {
  .vue-flow__edge-path {
    @apply !stroke-blue-700;
  }
}
</style>
