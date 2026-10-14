import api from './client'

export async function login(username: string, password: string) {
  const { data } = await api.post('/api/auth/login/', {
    username,
    password,
  })
  localStorage.setItem('access', data.access)
  localStorage.setItem('refresh', data.refresh)
  return data
}

export function logout() {
  localStorage.removeItem('access')
  localStorage.removeItem('refresh')
}

export function isLoggedIn() {
  return !!localStorage.getItem('access')
}