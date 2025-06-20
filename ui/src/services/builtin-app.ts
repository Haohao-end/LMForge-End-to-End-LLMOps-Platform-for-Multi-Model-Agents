import { get, post } from '@/utils/request'
import type { GetBuiltinAppCategoriesResponse, GetBuiltinAppsResponse } from '@/models/builtin-app'
import type { BaseResponse } from '@/models/base'

// 获取内置应用分类列表
export const getBuiltinAppCategories = () => {
  return get<GetBuiltinAppCategoriesResponse>(`/builtin-apps/categories`)
}

// 获取内置应用列表信息
export const getBuiltinApps = () => {
  return get<GetBuiltinAppsResponse>(`/builtin-apps`)
}

// 将指定 Agent 模板添加到工作区
export const addBuiltinAppToSpace = (builtin_app_id: string) => {
  return post<BaseResponse<{ id: string }>>(`/builtin-apps/add-builtin-app-to-space`, {
    body: { builtin_app_id },
  })
}
