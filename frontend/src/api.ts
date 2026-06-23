const BASE = "http://127.0.0.1:8000"

export type Task = {
  id: string
  title: string
  description: string
  status: "pending" | "in_progress" | "done" | "failed"
  result: string
  created_at: string
  updated_at: string
}

export async function listTasks(): Promise<Task[]> {
  const r = await fetch(`${BASE}/tasks`)
  return r.json()
}

export async function createTask(title: string, description: string): Promise<Task> {
  const r = await fetch(`${BASE}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description }),
  })
  return r.json()
}
