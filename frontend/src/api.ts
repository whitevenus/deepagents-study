const BASE = "http://127.0.0.1:8000"

export type Task = {
  id: string
  title: string
  description: string
  status: "pending" | "decomposing" | "in_progress" | "done" | "failed" | "cancelled"
  result: string
  parent_id: string | null
  created_at: string
  updated_at: string
}

export async function listTasks(): Promise<Task[]> {
  const r = await fetch(`${BASE}/tasks`)
  return r.json()
}

export async function createTask(
  title: string,
  description: string,
  decompose = false,
): Promise<Task> {
  const r = await fetch(`${BASE}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description, decompose }),
  })
  return r.json()
}

export async function cancelTask(id: string): Promise<Task> {
  const r = await fetch(`${BASE}/tasks/${id}/cancel`, { method: "POST" })
  return r.json()
}
