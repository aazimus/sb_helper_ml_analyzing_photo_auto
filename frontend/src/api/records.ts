import api from './client'

export interface RecordItem {
  id: number
  plate_number: string
  group_name: string
  status: string
  created_at: string
  crop_url: string | null
  original_url: string | null
}

export interface RecordsResponse {
  count: number
  next: string | null
  previous: string | null
  results: RecordItem[]
}

export async function getRecords(params: {
  group?: string
  search?: string
  date_from?: string
  date_to?: string
  page?: number
}) {
  const { data } = await api.get<RecordsResponse>('/api/records/', { params })
  return data
}

export async function getGroups() {
  const { data } = await api.get<string[]>('/api/groups/')
  return data
}