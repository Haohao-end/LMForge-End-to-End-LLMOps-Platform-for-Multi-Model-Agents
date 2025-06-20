import { ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  type CreateApiKeyRequest,
  type GetApiKeysWithPageResponse,
  type UpdateApiKeyRequest,
} from '@/models/api-key'
import {
  createApiKey,
  deleteApiKey,
  getApiKeysWithPage,
  updateApiKey,
  updateApiKeyIsActive,
} from '@/services/api-key'
import { Message, Modal } from '@arco-design/web-vue'

export const useGetApiKeysWithPage = () => {
  // 1.定义hooks所需数据
  const route = useRoute()
  const loading = ref(false)
  const api_keys = ref<GetApiKeysWithPageResponse['data']['list']>([])
  const defaultPaginator = {
    current_page: 1,
    page_size: 20,
    total_page: 0,
    total_record: 0,
  }
  const paginator = ref({ ...defaultPaginator })

  // 2.定义加载数据函数
  // In useGetApiKeysWithPage hook, update the loadApiKeys function:
const loadApiKeys = async (init: boolean = false) => {
  if (!init && paginator.value.current_page > paginator.value.total_page) {
    return
  }

  try {
    loading.value = true
    const resp = await getApiKeysWithPage({
      current_page: (route.query?.current_page || 1) as number,
      page_size: (route.query?.page_size || 20) as number,
    })
    const data = resp.data

    // Parse the list string into an array
    const parsedList = JSON.parse(data.list as unknown as string)
    
    paginator.value = data.paginator
    api_keys.value = parsedList // Use the parsed array
  } finally {
    loading.value = false
  }
}

  return { loading, api_keys, paginator, loadApiKeys }
}

export const useDeleteApiKey = () => {
  const handleDeleteApiKey = (api_key_id: string, callback?: () => void) => {
    Modal.warning({
      title: '要删除该API秘钥吗?',
      content:
        '删除秘钥后，无法使用该秘钥访问 LLMOps 个人空间中的所有 Agent，并且无法恢复，如果临时关闭请使用禁用功能。',
      hideCancel: false,
      onOk: async () => {
        try {
          // 1.点击确定后向API接口发起请求
          const resp = await deleteApiKey(api_key_id)
          Message.success(resp.message)
        } finally {
          // 2.调用callback函数指定回调功能
          callback && callback()
        }
      },
    })
  }

  return { handleDeleteApiKey }
}

export const useUpdateApiKey = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义更新处理器
  const handleUpdateApiKey = async (api_key_id: string, req: UpdateApiKeyRequest) => {
    try {
      loading.value = true
      const resp = await updateApiKey(api_key_id, req)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handleUpdateApiKey }
}

export const useUpdateApiKeyIsActive = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义更新处理器
  const handleUpdateApiKeyIsActive = async (
    api_key_id: string,
    is_active: boolean,
    callback?: () => void,
  ) => {
    try {
      loading.value = true
      const resp = await updateApiKeyIsActive(api_key_id, is_active)
      Message.success(resp.message)
    } finally {
      loading.value = false
      callback && callback()
    }
  }

  return { loading, handleUpdateApiKeyIsActive }
}

export const useCreateApiKey = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义更新处理器
  const handleCreateApiKey = async (req: CreateApiKeyRequest) => {
    try {
      loading.value = true
      const resp = await createApiKey(req)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handleCreateApiKey }
}
