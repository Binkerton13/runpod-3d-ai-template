export async function pingBackend() {
  try {
    const res = await fetch('/api/health')
    return res.ok
  } catch {
    return false
  }
}
