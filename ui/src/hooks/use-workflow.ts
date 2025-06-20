import { ref } from 'vue'
import type {
  CreateWorkflowRequest,
  GetWorkflowsWithPageResponse,
  UpdateDraftGraphRequest,
  UpdateWorkflowRequest,
} from '@/models/workflow'
import {
  cancelPublishWorkflow,
  createWorkflow,
  debugWorkflow,
  deleteWorkflow,
  getDraftGraph,
  getWorkflow,
  getWorkflowsWithPage,
  publishWorkflow,
  updateDraftGraph,
  updateWorkflow,
} from '@/services/workflow'
import { useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'

export const useGetWorkflowsWithPage = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)
  const workflows = ref<GetWorkflowsWithPageResponse['data']['list']>([])
  const defaultPaginator = {
    current_page: 1,
    page_size: 20,
    total_page: 0,
    total_record: 0,
  }
  const paginator = ref({ ...defaultPaginator })

  // 2.定义加载数据函数
  const loadWorkflows = async (
    search_word: string = '',
    status: string = '',
    init: boolean = false,
  ) => {
    // 2.1 判断是否是初始化，并检查分页器
    if (init) {
      paginator.value = defaultPaginator
    } else if (paginator.value.current_page > paginator.value.total_page) {
      return
    }

    try {
      // 2.2 调用接口获取响应数据
      loading.value = true
      const resp = await getWorkflowsWithPage({
        current_page: paginator.value.current_page,
        page_size: paginator.value.page_size,
        search_word,
        status,
      })
      const data = resp.data

      // 2.3 更新分页器
      paginator.value = data.paginator

      // 2.4 判断是否存在更多数据
      if (paginator.value.current_page <= paginator.value.total_page) {
        paginator.value.current_page += 1
      }

      // 2.5 判断是追加或者是覆盖数据
      if (init) {
        workflows.value = data.list
      } else {
        workflows.value.push(...data.list)
      }
    } finally {
      loading.value = false
    }
  }

  return { loading, workflows, paginator, loadWorkflows }
}

export const useCreateWorkflow = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)
  const router = useRouter()

  // 2.定义创建工作流处理器
  const handleCreateWorkflow = async (req: CreateWorkflowRequest) => {
    try {
      // 3.调用API接口创建工作流
      loading.value = true
      const resp = await createWorkflow(req)

      // 4.创建成功提示并跳转页面
      Message.success('创建工作流成功')
      await router.push({
        name: 'space-workflows-detail',
        params: {
          workflow_id: resp.data.id,
        },
      })
    } finally {
      loading.value = false
    }
  }

  return { loading, handleCreateWorkflow }
}

export const useUpdateWorkflow = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义更新工作流处理器
  const handleUpdateWorkflow = async (workflow_id: string, req: UpdateWorkflowRequest) => {
    try {
      // 3.调用api接口更新工作流
      loading.value = true
      const resp = await updateWorkflow(workflow_id, req)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handleUpdateWorkflow }
}

export const useGetWorkflow = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)
  const workflow = ref<Record<string, any>>({})

  // 2.定义或区间数据函数
  const loadWorkflow = async (workflow_id: string) => {
    try {
      // 3.调用API接口获取工作流基础信息
      loading.value = true
      const resp = await getWorkflow(workflow_id)
      workflow.value = resp.data
    } finally {
      loading.value = false
    }
  }

  return { loading, workflow, loadWorkflow }
}

export const useDeleteWorkflow = () => {
  const handleDeleteWorkflow = (workflow_id: string, callback?: () => void) => {
    Modal.warning({
      title: '要删除该工作流吗?',
      content:
        '删除工作流后，发布的WebApp、开放API以及关联的社交媒体平台均无法使用该工作流，如果需要暂停工作流，可使用取消发布功能。',
      hideCancel: false,
      onOk: async () => {
        try {
          // 1.点击确定后向API接口发起请求
          const resp = await deleteWorkflow(workflow_id)
          Message.success(resp.message)
        } finally {
          // 2.调用callback函数指定回调功能
          callback && callback()
        }
      },
    })
  }

  return { handleDeleteWorkflow }
}

export const useGetDraftGraph = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)
  const nodes = ref<any[]>([])
  const edges = ref<any[]>([])

  // 2.定义加载数据函数
  const loadDraftGraph = async (workflow_id: string) => {
    try {
      // 3.调用api获取数据
      loading.value = true
      const resp = await getDraftGraph(workflow_id)
      const data = resp.data

      // 4.处理节点数据并赋值
      nodes.value = data.nodes.map((node) => {
        // 5.删除不传递的数据并构建新节点数据存储到data中
        const { id, node_type: type, position, ...data } = node
        return { id, type, position, data }
      })

      // 6.处理边数据
      edges.value = data.edges.map((edge) => {
        // 7.添加动画，并设置边的粗细+颜色
        return { ...edge, animated: true, style: { strokeWidth: 2, stroke: '#9ca3af' } }
      })
    } finally {
      loading.value = false
    }
  }

  return { loading, nodes, edges, loadDraftGraph }
}

export const useUpdateDraftGraph = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义更新草稿图配置处理器
  const handleUpdateDraftGraph = async (
    workflow_id: string,
    req: UpdateDraftGraphRequest,
    is_notify: boolean = true,
  ) => {
    try {
      // 3.调用api接口更新草稿图配置
      loading.value = true
      const resp = await updateDraftGraph(workflow_id, req)
      is_notify && Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  // 3.定义图配置数据转请求数据函数
  const convertGraphToReq = (
    nodes: Record<string, any>[],
    edges: Record<string, any>[],
  ): UpdateDraftGraphRequest => {
    return {
      nodes: nodes.map((node) => {
        return {
          id: node.id,
          node_type: node.type,
          position: node.position,
          ...node.data,
        }
      }),
      edges: edges.map((edge) => {
        return {
          id: edge.id,
          source: edge.source,
          source_type: edge.source_type,
          target: edge.target,
          target_type: edge.target_type,
        }
      }),
    }
  }

  return { loading, convertGraphToReq, handleUpdateDraftGraph }
}

export const usePublishWorkflow = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义发布工作流处理器
  const handlePublishWorkflow = async (workflow_id: string) => {
    try {
      // 3.调用api接口发布工作流
      loading.value = true
      const resp = await publishWorkflow(workflow_id)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handlePublishWorkflow }
}

export const useCancelPublishWorkflow = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义取消发布处理器
  const handleCancelPublish = async (workflow_id: string) => {
    try {
      // 3.调用api取消发布工作流
      loading.value = true
      const resp = await cancelPublishWorkflow(workflow_id)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handleCancelPublish }
}

export const useDebugWorkflow = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)
  const error = ref('')

  // 2.定义调试会话处理器
  const handleDebugWorkflow = async (
    workflow_id: string,
    inputs: Record<string, any>,
    onData: (event_response: Record<string, any>) => void,
  ) => {
    try {
      loading.value = true
      const resp = await debugWorkflow(workflow_id, inputs, onData)

      // 2.1 判断响应内容是否存在，如果存在则表示该接口为非流式输出，意味着接口出错
      if (resp !== undefined) {
        error.value = resp['message']
      }
    } finally {
      loading.value = false
    }
  }

  return { loading, error, handleDebugWorkflow }
}
