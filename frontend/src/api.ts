const BASE = "http://127.0.0.1:8000"

// JWT 存 localStorage。所有请求带 Authorization: Bearer。
export function getToken(): string | null {
  return localStorage.getItem("token")
}
function setToken(t: string) {
  localStorage.setItem("token", t)
}
export function logout() {
  localStorage.removeItem("token")
}

function authHeaders(extra: Record<string, string> = {}) {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}`, ...extra } : extra
}

export type Task = {
  id: string
  title: string
  description: string
  status: "pending" | "decomposing" | "in_progress" | "done" | "failed" | "cancelled"
  result: string
  parent_id: string | null
  owner_id: string | null
  created_at: string
  updated_at: string
}

export type Me = { username: string; roles: string[] }

async function ok(r: Response) {
  if (r.status === 401) {
    logout() // token 失效/过期 → 清掉,App 会跳回登录
    throw new Error("登录已失效")
  }
  if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail || `HTTP ${r.status}`)
  return r.json()
}

export async function login(username: string, password: string): Promise<void> {
  // OAuth2 标准登录:表单字段 username/password
  const body = new URLSearchParams({ username, password })
  const r = await fetch(`${BASE}/auth/login`, { method: "POST", body })
  if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail || "登录失败")
  setToken((await r.json()).access_token)
}

export async function getMe(): Promise<Me> {
  return ok(await fetch(`${BASE}/auth/me`, { headers: authHeaders() }))
}

export async function listTasks(): Promise<Task[]> {
  return ok(await fetch(`${BASE}/tasks`, { headers: authHeaders() }))
}

export async function createTask(
  title: string,
  description: string,
  decompose = false,
): Promise<Task> {
  return ok(
    await fetch(`${BASE}/tasks`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ title, description, decompose }),
    }),
  )
}

export async function cancelTask(id: string): Promise<Task> {
  return ok(await fetch(`${BASE}/tasks/${id}/cancel`, { method: "POST", headers: authHeaders() }))
}
