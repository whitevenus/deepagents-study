const BASE = "http://127.0.0.1:8000"

// 身份(stub):谁都能切。真登录留到 Phase 3 UI。后端按 X-User-Id 做权限。
export const USERS = ["alice", "bob", "carol"] as const // admin / member / viewer
export function getUser(): string {
  return localStorage.getItem("user") || "alice"
}
export function setUser(u: string) {
  localStorage.setItem("user", u)
}
function headers(extra: Record<string, string> = {}) {
  return { "X-User-Id": getUser(), ...extra }
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

async function ok(r: Response) {
  if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail || `HTTP ${r.status}`)
  return r.json()
}

export async function listTasks(): Promise<Task[]> {
  return ok(await fetch(`${BASE}/tasks`, { headers: headers() }))
}

export async function createTask(
  title: string,
  description: string,
  decompose = false,
): Promise<Task> {
  return ok(
    await fetch(`${BASE}/tasks`, {
      method: "POST",
      headers: headers({ "Content-Type": "application/json" }),
      body: JSON.stringify({ title, description, decompose }),
    }),
  )
}

export async function cancelTask(id: string): Promise<Task> {
  return ok(await fetch(`${BASE}/tasks/${id}/cancel`, { method: "POST", headers: headers() }))
}
