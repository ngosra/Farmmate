import { StatusBar } from 'expo-status-bar'
import { useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'
const GREEN = '#0AB187'
const FOREST = '#10241C'

type Me = {
  id: string
  email: string
  farmer_id: string | null
  organization: { id: string; name: string; role: string } | null
}

type Session = {
  access: string
  refresh: string
  me: Me
}

const TABS = ['Home', 'Chat', 'Reports', 'Trace'] as const
type Tab = (typeof TABS)[number]

async function signIn(identifier: string, password: string): Promise<Session> {
  const response = await fetch(`${API_URL}/api/v1/auth/login/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-FarmMate-Client': 'mobile',
    },
    body: JSON.stringify({ identifier, password }),
  })
  if (!response.ok) {
    throw new Error('Unknown identifier or password.')
  }
  const body = (await response.json()) as { access: string; refresh: string }
  const meResponse = await fetch(`${API_URL}/api/v1/auth/me/`, {
    headers: { Authorization: `Bearer ${body.access}` },
  })
  if (!meResponse.ok) {
    throw new Error('Could not load your account.')
  }
  const me = (await meResponse.json()) as Me
  return { access: body.access, refresh: body.refresh, me }
}

export default function App() {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [session, setSession] = useState<Session | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<Tab>('Home')

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
          onTab={setTab}
          onSignOut={() => setSession(null)}
        />
      ) : (
        <View style={styles.login}>
          <Text style={styles.brand}>FarmMate</Text>
          <Text style={styles.lede}>Farmer field app. An administrator creates your login.</Text>
          <Text style={styles.label}>Email or FarmerID</Text>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            value={identifier}
            onChangeText={setIdentifier}
            style={styles.input}
          />
          <Text style={styles.label}>Password</Text>
          <TextInput
            secureTextEntry
            value={password}
            onChangeText={setPassword}
            style={styles.input}
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Pressable style={styles.button} onPress={() => void onSignIn()} disabled={busy}>
            {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Sign in</Text>}
          </Pressable>
          <Text style={styles.note}>There is no public signup. Contact your administrator.</Text>
        </View>
      )}
    </View>
  )
}

function SignedIn({
  session,
  tab,
  onTab,
  onSignOut,
}: {
  session: Session
  tab: Tab
  onTab: (tab: Tab) => void
  onSignOut: () => void
}) {
  const name = session.me.farmer_id ?? session.me.email
  return (
    <View style={styles.signedIn}>
      <View style={styles.header}>
        <Text style={styles.brand}>FarmMate</Text>
        <Pressable onPress={onSignOut}>
          <Text style={styles.signOut}>Sign out</Text>
        </Pressable>
      </View>
      <View style={styles.body}>
        <Text style={styles.heading}>{tab}</Text>
        {tab === 'Home' ? (
          <Text style={styles.lede}>Signed in as {name}. Field records are not in this scaffold yet.</Text>
        ) : (
          <Text style={styles.lede}>{tab} is not available in this scaffold yet.</Text>
        )}
      </View>
      <View style={styles.tabs}>
        {TABS.map((item) => (
          <Pressable key={item} onPress={() => onTab(item)} style={styles.tab}>
            <Text style={item === tab ? styles.tabActive : styles.tabLabel}>{item}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#F4F7F5' },
  login: { flex: 1, justifyContent: 'center', padding: 24, gap: 8 },
  brand: { color: GREEN, fontSize: 28, fontWeight: '700' },
  lede: { color: '#5D6F67', fontSize: 16, marginBottom: 8 },
  label: { color: FOREST, fontWeight: '600', marginTop: 8 },
  input: {
    backgroundColor: '#fff',
    borderColor: '#D5E3DC',
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
  },
  button: {
    marginTop: 16,
    backgroundColor: GREEN,
    borderRadius: 10,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  error: { color: '#9F2D2D' },
  note: { color: '#5D6F67', marginTop: 12 },
  signedIn: { flex: 1, backgroundColor: FOREST },
  header: {
    paddingTop: 64,
    paddingHorizontal: 20,
    paddingBottom: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  signOut: { color: '#fff', fontWeight: '600' },
  body: {
    flex: 1,
    backgroundColor: '#F4F7F5',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
  },
  heading: { fontSize: 24, fontWeight: '700', color: FOREST, marginBottom: 8 },
  tabs: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderTopColor: '#D5E3DC',
    borderTopWidth: 1,
    paddingBottom: 18,
    paddingTop: 10,
  },
  tab: { flex: 1, alignItems: 'center' },
  tabLabel: { color: '#5D6F67', fontWeight: '600' },
  tabActive: { color: GREEN, fontWeight: '700' },
})
