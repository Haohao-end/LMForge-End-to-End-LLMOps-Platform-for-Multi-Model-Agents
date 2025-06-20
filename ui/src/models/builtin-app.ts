import type { BaseResponse } from '@/models/base'

// 获取内置应用分类响应结构体
export type GetBuiltinAppCategoriesResponse = BaseResponse<
  {
    category: string
    name: string
  }[]
>

// 获取内置应用列表响应结构体
export type GetBuiltinAppsResponse = BaseResponse<
  {
    id: string
    category: string
    name: string
    icon: string
    description: string
    model_config: {
      provider: string
      model: string
    }
    created_at: number
  }[]
>
