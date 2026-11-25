import AsyncStorage from '@react-native-async-storage/async-storage'

const KEY = 'farmmate.pending'

export type PendingRecord = {
  id: string
  label: string
  path: string
  body: unknown
}

export async function readQueue(): Promise<PendingRecord[]> {
  const raw = await AsyncStorage.getItem(KEY)
  if (!raw) return []
  const parsed = JSON.parse(raw) as PendingRecord[]
  return Array.isArray(parsed) ? parsed : []
}

export async function writeQueue(records: PendingRecord[]) {
  await AsyncStorage.setItem(KEY, JSON.stringify(records))
}

export async function enqueue(record: PendingRecord) {
  const current = await readQueue()
  await writeQueue([record, ...current])
}
