import { get, post } from '@/utils/request'
import type { BaseResponse } from '@/models/base'
import type {
  CreateMcpProviderRequest,
  GetMcpCategoriesResponse,
  GetMcpProviderResponse,
  GetMcpProvidersWithPageRequest,
  GetMcpProvidersWithPageResponse,
  UpdateMcpProviderRequest,
} from '@/models/mcp'

export const getMcpCategories = () => {
  return get<GetMcpCategoriesResponse>('/mcp-providers/categories')
}

export const getPublicMcpCategories = () => {
  return get<GetMcpCategoriesResponse>('/public/mcp-providers/categories')
}

export const getPublicMcpProvidersWithPage = (params: GetMcpProvidersWithPageRequest) => {
  return get<GetMcpProvidersWithPageResponse>('/public/mcp-providers', { params })
}

export const getPublicMcpProvider = (provider_key: string) => {
  return get<GetMcpProviderResponse>(`/public/mcp-providers/${encodeURIComponent(provider_key)}`)
}

export const getMcpProvidersWithPage = (params: GetMcpProvidersWithPageRequest) => {
  return get<GetMcpProvidersWithPageResponse>('/mcp-providers', { params })
}

export const getMcpProvider = (provider_id: string) => {
  return get<GetMcpProviderResponse>(`/mcp-providers/${provider_id}`)
}

export const createMcpProvider = (req: CreateMcpProviderRequest) => {
  return post<BaseResponse<{ id: string }>>('/mcp-providers', { body: req })
}

export const updateMcpProvider = (provider_id: string, req: UpdateMcpProviderRequest) => {
  return post<BaseResponse<any>>(`/mcp-providers/${provider_id}`, { body: req })
}

export const deleteMcpProvider = (provider_id: string) => {
  return post<BaseResponse<any>>(`/mcp-providers/${provider_id}/delete`)
}

export const publishMcpProvider = (provider_id: string) => {
  return post<BaseResponse<any>>(`/mcp-providers/${provider_id}/publish`)
}

export const unpublishMcpProvider = (provider_id: string) => {
  return post<BaseResponse<any>>(`/mcp-providers/${provider_id}/unpublish`)
}

export const regenerateMcpIcon = (provider_id: string) => {
  return post<BaseResponse<{ icon: string }>>(`/mcp-providers/${provider_id}/regenerate-icon`)
}

export const generateMcpIconPreview = (name: string, description: string) => {
  return post<BaseResponse<{ icon: string }>>('/mcp-providers/generate-icon-preview', {
    body: { name, description },
  })
}
