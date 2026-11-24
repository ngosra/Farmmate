import { CameraView, useCameraPermissions } from 'expo-camera'
import * as Location from 'expo-location'
import { StatusBar } from 'expo-status-bar'
import { useEffect, useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { OfflineError, api, batchCode, signIn, type Session } from './src/client'
import { enqueue, readQueue, writeQueue, type PendingRecord } from './src/queue'

const GREEN = '#0AB187'
const FOREST = '#10241C'
const TABS = ['Home', 'Record', 'Farms', 'Trace', 'Ask'] as const
type Tab = (typeof TABS)[number]

type Dashboard = {
  farmers: number
  farms: number
  fields: number
  production: { harvest_kg: string | number }
  recommendations: { text: string; basis: string }[]
}
type Farm = { id: string; name: string; code: string; field_count: number }
type Trace = { verification: { batch: string; product_name: string; status: string } }

export default function App() {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [session, setSession] = useState<Session | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<Tab>('Home')
  const [pending, setPending] = useState(0)

  useEffect(() => {
    void readQueue().then((rows) => setPending(rows.length))
  }, [])

  async function onSignIn() {
    setBusy(true)
    setError(null)
    try {
      setSession(await signIn(identifier.trim(), password))
      setTab('Home')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <View style={styles.screen}>
      <StatusBar style="light" />
      {session ? (
        <SignedIn
          session={session}
          tab={tab}
          pending={pending}
          onTab={setTab}
          onPending={setPending}
          onSignOut={() => setSession(null)}
        />
      ) : (
        <View style={styles.login}>
          <Text style={styles.brand}>FarmMate</Text>
          <Text style={styles.lede}>Field records for farmers. An administrator creates your login.</Text>
          <Text style={styles.label}>Email or FarmerID</Text>
          <TextInput autoCapitalize="none" autoCorrect={false} value={identifier} onChangeText={setIdentifier} style={styles.input} />
          <Text style={styles.label}>Password</Text>
          <TextInput secureTextEntry value={password} onChangeText={setPassword} style={styles.input} />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Pressable style={styles.button} onPress={() => void onSignIn()} disabled={busy}>
            {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Sign in</Text>}
          </Pressable>
        </View>
      )}
    </View>
  )
}

function SignedIn({
  session,
  tab,
  pending,
  onTab,
  onPending,
  onSignOut,
}: {
  session: Session
  tab: Tab
  pending: number
  onTab: (tab: Tab) => void
  onPending: (count: number) => void
  onSignOut: () => void
}) {
  return (
    <View style={styles.signedIn}>
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>FarmMate</Text>
          <Text style={styles.headerMeta}>{session.me.organization?.name ?? session.me.email}</Text>
        </View>
        <Pressable onPress={onSignOut}><Text style={styles.signOut}>Sign out</Text></Pressable>
      </View>
      <View style={styles.body}>
        {tab === 'Home' ? <Home session={session} pending={pending} onPending={onPending} /> : null}
        {tab === 'Record' ? <Record session={session} onQueued={() => onPending(pending + 1)} /> : null}
        {tab === 'Farms' ? <Farms session={session} /> : null}
        {tab === 'Trace' ? <TraceTab session={session} /> : null}
        {tab === 'Ask' ? <Ask session={session} /> : null}
      </View>
      <View style={styles.tabs}>
        {TABS.map((item) => (
          <Pressable key={item} onPress={() => onTab(item)} style={styles.tab}>
            <Text style={item === tab ? styles.tabActive : styles.tabLabel}>
              {item === 'Home' && pending ? `Home ${pending}` : item}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  )
}

function Home({
  session,
  pending,
  onPending,
}: {
  session: Session
  pending: number
  onPending: (count: number) => void
}) {
  const [data, setData] = useState<Dashboard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    void api<Dashboard>(session, '/api/v1/dashboard/')
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Could not load the farm.'))
  }, [session])

  async function sync() {
    setSyncing(true)
    setError(null)
    const queue = await readQueue()
    const left: PendingRecord[] = []
    let note = ''
    for (const row of queue) {
      try {
        await api(session, row.path, { method: 'POST', body: JSON.stringify(row.body) })
      } catch (err) {
        left.push(row)
        if (!(err instanceof OfflineError) && !note && err instanceof Error) note = err.message
      }
    }
    await writeQueue(left)
    onPending(left.length)
    setSyncing(false)
    if (left.length) setError(note || `${left.length} record(s) are still waiting.`)
  }

  return (
    <ScrollView contentContainerStyle={styles.stack}>
      <Text style={styles.heading}>Today</Text>
      <Text style={styles.lede}>
        {session.me.farmer_id ? `FarmerID ${session.me.farmer_id}. ` : ''}
        {pending} record{pending === 1 ? '' : 's'} waiting to sync.
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {data ? (
        <View style={styles.stats}>
          <Stat label="Farms" value={String(data.farms)} />
          <Stat label="Fields" value={String(data.fields)} />
          <Stat label="Harvest kg" value={String(data.production.harvest_kg)} />
        </View>
      ) : (
        <Text style={styles.lede}>Loading your records…</Text>
      )}
      {(data?.recommendations ?? []).slice(0, 3).map((row) => (
        <Text key={row.text} style={styles.card}>{row.text}</Text>
      ))}
      <Pressable style={styles.button} onPress={() => void sync()} disabled={syncing}>
        <Text style={styles.buttonText}>{syncing ? 'Syncing…' : 'Sync saved records'}</Text>
      </Pressable>
    </ScrollView>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  )
}

function Record({ session, onQueued }: { session: Session; onQueued: () => void }) {
  const [farms, setFarms] = useState<Farm[]>([])
  const [farmId, setFarmId] = useState('')
  const [kind, setKind] = useState('weeding')
  const [notes, setNotes] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    void api<{ results: Farm[] }>(session, '/api/v1/farms/')
      .then((page) => {
        setFarms(page.results)
        setFarmId(page.results[0]?.id ?? '')
      })
      .catch(() => setError('Farms could not be loaded. You can still type a note and save it offline after a farm is chosen.'))
  }, [session])

  async function locate() {
    setError('')
    const permission = await Location.requestForegroundPermissionsAsync()
    if (!permission.granted) {
      setError('Location permission was not granted.')
      return
    }
    const position = await Location.getCurrentPositionAsync({})
    setNotes((current) =>
      `${current}\nGPS ${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`.trim(),
    )
  }

  async function save() {
    setError('')
    setMessage('')
    if (!farmId) {
      setError('Choose a farm first. That list needs a connection.')
      return
    }
    const body = {
      farm: farmId,
      kind,
      occurred_on: new Date().toISOString().slice(0, 10),
      notes,
    }
    try {
      await api(session, '/api/v1/activities/', { method: 'POST', body: JSON.stringify(body) })
      setMessage('Activity saved.')
      setNotes('')
    } catch (err) {
      if (err instanceof OfflineError) {
        await enqueue({
          id: `${Date.now()}`,
          label: `${kind} activity`,
          path: '/api/v1/activities/',
          body,
        })
        onQueued()
        setMessage('No connection. The activity is saved on this phone.')
        setNotes('')
        return
      }
      setError(err instanceof Error ? err.message : 'Could not save the activity.')
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.stack}>
      <Text style={styles.heading}>Record work</Text>
      <Text style={styles.label}>Farm</Text>
      {farms.map((farm) => (
        <Pressable key={farm.id} onPress={() => setFarmId(farm.id)} style={farmId === farm.id ? styles.choiceOn : styles.choice}>
          <Text style={styles.choiceText}>{farm.name}</Text>
        </Pressable>
      ))}
      <Text style={styles.label}>Kind</Text>
      <View style={styles.row}>
        {['weeding', 'spraying', 'fertilizing', 'planting'].map((item) => (
          <Pressable key={item} onPress={() => setKind(item)} style={kind === item ? styles.choiceOn : styles.choice}>
            <Text style={styles.choiceText}>{item}</Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.label}>Notes</Text>
      <TextInput multiline value={notes} onChangeText={setNotes} style={[styles.input, styles.notes]} />
      <Pressable style={styles.secondary} onPress={() => void locate()}><Text style={styles.secondaryText}>Add GPS</Text></Pressable>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {message ? <Text style={styles.ok}>{message}</Text> : null}
      <Pressable style={styles.button} onPress={() => void save()}><Text style={styles.buttonText}>Save activity</Text></Pressable>
    </ScrollView>
  )
}

function Farms({ session }: { session: Session }) {
  const [rows, setRows] = useState<Farm[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    void api<{ results: Farm[] }>(session, '/api/v1/farms/')
      .then((page) => setRows(page.results))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Could not load farms.'))
  }, [session])
  return (
    <ScrollView contentContainerStyle={styles.stack}>
      <Text style={styles.heading}>Farms</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {rows.length === 0 ? <Text style={styles.lede}>No farms are on this account yet.</Text> : null}
      {rows.map((farm) => (
        <View key={farm.id} style={styles.card}>
          <Text style={styles.choiceText}>{farm.name}</Text>
          <Text style={styles.lede}>{farm.code} · {farm.field_count} fields</Text>
        </View>
      ))}
    </ScrollView>
  )
}

function TraceTab({ session }: { session: Session }) {
  const [permission, requestPermission] = useCameraPermissions()
  const [scanning, setScanning] = useState(false)
  const [code, setCode] = useState('')
  const [result, setResult] = useState<Trace | null>(null)
  const [error, setError] = useState('')

  async function lookup(raw: string) {
    const value = batchCode(raw)
    if (!value) return
    setError('')
    setScanning(false)
    try {
      setResult(await api<Trace>(session, `/api/v1/trace/${encodeURIComponent(value)}/`))
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'Could not verify that batch.')
    }
  }

  return (
    <View style={styles.stackFill}>
      <Text style={styles.heading}>Batch check</Text>
      {scanning && permission?.granted ? (
        <CameraView
          style={styles.camera}
          barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
          onBarcodeScanned={({ data }) => {
            setCode(data)
            void lookup(data)
          }}
        />
      ) : null}
      <TextInput value={code} onChangeText={setCode} autoCapitalize="none" placeholder="Batch code" style={styles.input} />
      <Pressable style={styles.button} onPress={() => void lookup(code)}><Text style={styles.buttonText}>Look up</Text></Pressable>
      <Pressable
        style={styles.secondary}
        onPress={() => {
          if (!permission?.granted) void requestPermission()
          setScanning((current) => !current)
        }}
      >
        <Text style={styles.secondaryText}>{scanning ? 'Close camera' : 'Scan QR'}</Text>
      </Pressable>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {result ? (
        <View style={styles.card}>
          <Text style={styles.choiceText}>{result.verification.product_name}</Text>
          <Text style={styles.lede}>{result.verification.batch} · {result.verification.status}</Text>
        </View>
      ) : null}
    </View>
  )
}

function Ask({ session }: { session: Session }) {
  const [question, setQuestion] = useState('What compliance evidence is missing?')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')

  async function ask() {
    setError('')
    try {
      const result = await api<{ answer: string }>(session, '/api/v1/assistant/', {
        method: 'POST',
        body: JSON.stringify({ question }),
      })
      setAnswer(result.answer)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not ask the assistant.')
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.stack}>
      <Text style={styles.heading}>Assistant</Text>
      <Text style={styles.lede}>Answers use your recorded farm data. Missing records stay missing.</Text>
      <TextInput multiline value={question} onChangeText={setQuestion} style={[styles.input, styles.notes]} />
      <Pressable style={styles.button} onPress={() => void ask()}><Text style={styles.buttonText}>Ask</Text></Pressable>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {answer ? <Text style={styles.card}>{answer}</Text> : null}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#F4F7F5' },
  login: { flex: 1, justifyContent: 'center', padding: 24, gap: 8 },
  brand: { color: GREEN, fontSize: 28, fontWeight: '700' },
  lede: { color: '#5D6F67', fontSize: 16 },
  label: { color: FOREST, fontWeight: '600', marginTop: 8 },
  input: {
    backgroundColor: '#fff',
    borderColor: '#D5E3DC',
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
  },
  notes: { minHeight: 96, textAlignVertical: 'top' },
  button: { marginTop: 8, backgroundColor: GREEN, borderRadius: 8, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  secondary: { borderColor: '#D5E3DC', borderWidth: 1, borderRadius: 8, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  secondaryText: { color: '#067A5E', fontWeight: '700' },
  error: { color: '#9F2D2D' },
  ok: { color: '#067A5E' },
  signedIn: { flex: 1, backgroundColor: FOREST },
  header: { paddingTop: 56, paddingHorizontal: 20, paddingBottom: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerMeta: { color: '#D7EBE3' },
  signOut: { color: '#fff', fontWeight: '600' },
  body: { flex: 1, backgroundColor: '#F4F7F5', padding: 16 },
  heading: { fontSize: 24, fontWeight: '700', color: FOREST },
  stack: { gap: 10, paddingBottom: 24 },
  stackFill: { flex: 1, gap: 10 },
  stats: { flexDirection: 'row', gap: 8 },
  stat: { flex: 1, backgroundColor: '#fff', borderRadius: 8, padding: 12, borderColor: '#D5E3DC', borderWidth: 1 },
  statValue: { fontSize: 22, fontWeight: '700', color: FOREST },
  statLabel: { color: '#5D6F67' },
  card: { backgroundColor: '#fff', borderRadius: 8, padding: 12, borderColor: '#D5E3DC', borderWidth: 1, color: FOREST },
  choice: { backgroundColor: '#fff', borderRadius: 8, padding: 10, borderColor: '#D5E3DC', borderWidth: 1 },
  choiceOn: { backgroundColor: '#E7F6F1', borderRadius: 8, padding: 10, borderColor: GREEN, borderWidth: 1 },
  choiceText: { color: FOREST, fontWeight: '700' },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  camera: { height: 220, borderRadius: 8, overflow: 'hidden' },
  tabs: { flexDirection: 'row', backgroundColor: '#fff', borderTopColor: '#D5E3DC', borderTopWidth: 1, paddingBottom: 18, paddingTop: 10 },
  tab: { flex: 1, alignItems: 'center' },
  tabLabel: { color: '#5D6F67', fontWeight: '600' },
  tabActive: { color: GREEN, fontWeight: '700' },
})
