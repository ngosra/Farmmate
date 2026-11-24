import { useState, type FormEvent } from 'react'
import { api, sendJson, type Page } from './api'
import { useAuth } from './useAuth'
import {
  Badge,
  Banner,
  Empty,
  LoadNote,
  PageHead,
  num,
  results,
  submitJson,
  useLoad,
} from './ui'

type Farmer = {
  id: string
  display_name: string
  farmer_id: string
  phone: string
  community: string
  region: string
}
type Farm = {
  id: string
  name: string
  code: string
  farmer: string
  latitude: string | null
  longitude: string | null
  field_count: number
  mapped_hectares: string | null
  status: string
}
type Field = {
  id: string
  farm: string
  name: string
  area_hectares: string | null
  missing_land_use_years: number[]
  boundary: { type: string; coordinates: number[][][] } | null
}
type Harvest = {
  id: string
  farm: string
  field: string
  harvested_on: string
  quantity_kg: string
}
type Batch = {
  id: string
  code: string
  public_code: string
  product_name: string
  balance: { sourced_kg: string; remaining_kg: string; balanced: boolean }
}
type Standard = { id: string; code: string; name: string; summary: string }
type Certification = {
  id: string
  standard_code?: string
  status: string
  farmer: string | null
  readiness: { readiness_percent: number | null; message: string; is_official_certification: boolean }
  items?: {
    id: string
    state: string
    requirement: { code: string; title: string; weight: number }
  }[]
}
type Product = {
  id: string
  name: string
  category: string
  unit: string
  on_hand: string
  reorder_level: string
}
type DashboardData = {
  farmers: number
  farms: number
  fields: number
  certification: {
    readiness_percent: number | null
    message: string
    verified_weight: number
    declared_weight: number
    missing_weight: number
    official: { id: string; standard: string; status: string; certificate_number: string; farmer: string | null }[]
  }
  production: { harvest_kg: string | number; activity_count: number }
  ndvi: { field_name: string; points: { date: string; ndvi_mean: string; source: string }[] }[]
  satellite_observations: number
  recent_activities: { id: string; kind: string; occurred_on: string; farm: string; notes: string }[]
  upcoming_inspections: { id: string; farm: string; scheduled_for: string; status: string }[]
  pending_actions: { id: string; title: string; due_on: string | null; status: string }[]
  recommendations: { text: string; basis: string }[]
}

function farmerName(farmers: Farmer[], id: string) {
  return farmers.find((farmer) => farmer.id === id)?.display_name ?? 'Farmer'
}

export function DashboardPage() {
  const { data, error, loading } = useLoad<DashboardData>('/api/v1/dashboard/')
  return (
    <>
      <PageHead
        title="Dashboard"
        lede="Counts and readiness come from records in this organization. A readiness score is not a certificate."
      />
      <Banner error={error} />
      <LoadNote loading={loading}>
        {data ? (
          <>
            <section className="stats">
              <article className="stat"><strong>{data.farmers}</strong><span>Farmers</span></article>
              <article className="stat"><strong>{data.farms}</strong><span>Farms</span></article>
              <article className="stat"><strong>{data.fields}</strong><span>Fields</span></article>
              <article className="stat">
                <strong>{num(data.production.harvest_kg)}</strong>
                <span>Harvest kg</span>
              </article>
            </section>
            <div className="split">
              <article className="card">
                <h2>Certification readiness</h2>
                {data.certification.readiness_percent === null ? (
                  <p>No checklist is open, so readiness is not calculated.</p>
                ) : (
                  <>
                    <strong>{data.certification.readiness_percent}%</strong>
                    <div className="meter" aria-hidden="true">
                      <span style={{ width: `${data.certification.readiness_percent}%` }} />
                    </div>
                  </>
                )}
                <p className="muted">{data.certification.message}</p>
                <p className="muted">
                  Verified weight {data.certification.verified_weight}, declared{' '}
                  {data.certification.declared_weight}, missing {data.certification.missing_weight}.
                </p>
                <h3>Official decisions</h3>
                {data.certification.official.length === 0 ? (
                  <p>No official certified decision is recorded.</p>
                ) : (
                  data.certification.official.map((row) => (
                    <p key={row.id}>
                      <Badge value={row.status} /> {row.standard} {row.certificate_number}{' '}
                      {row.farmer ? `· ${row.farmer}` : ''}
                    </p>
                  ))
                )}
              </article>
              <article className="card">
                <h2>Next records to add</h2>
                {data.recommendations.length === 0 ? (
                  <p>Nothing is flagged from the current records.</p>
                ) : (
                  data.recommendations.map((row) => (
                    <p key={row.text}>
                      <Badge value={row.basis} /> {row.text}
                    </p>
                  ))
                )}
              </article>
            </div>
            <article className="card">
              <h2>Recent activity</h2>
              {data.recent_activities.length === 0 ? (
                <Empty title="No activities yet" body="Planting, spraying, and other work will be listed here." />
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>Date</th><th>Farm</th><th>Kind</th><th>Notes</th></tr></thead>
                    <tbody>
                      {data.recent_activities.map((row) => (
                        <tr key={row.id}>
                          <td>{row.occurred_on}</td><td>{row.farm}</td><td>{row.kind}</td><td>{row.notes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </article>
            <article className="card">
              <h2>NDVI</h2>
              {data.ndvi.length === 0 ? (
                <p>
                  No observations are stored. Satellite readings: {data.satellite_observations}. FarmMate
                  does not invent vegetation data.
                </p>
              ) : (
                data.ndvi.map((field) => (
                  <p key={field.field_name}>
                    {field.field_name}:{' '}
                    {field.points.map((point) => `${point.date} ${point.ndvi_mean} (${point.source})`).join(', ')}
                  </p>
                ))
              )}
            </article>
          </>
        ) : null}
      </LoadNote>
    </>
  )
}

export function FarmersPage() {
  const list = useLoad<Page<Farmer>>('/api/v1/farmers/')
  const [error, setError] = useState<string | null>(null)
  const farmers = results(list.data)

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/farmers/', 'POST', {
        display_name: data.get('display_name'),
        farmer_id: data.get('farmer_id'),
        phone: data.get('phone'),
        community: data.get('community'),
        region: data.get('region'),
      })
      form.reset()
      await list.reload()
    }, setError)
  }

  return (
    <>
      <PageHead title="Farmers" lede="Farmer profiles stay inside this organization." />
      <Banner error={error || list.error} />
      <form className="card" onSubmit={(event) => void onCreate(event)}>
        <h2>Register a farmer</h2>
        <div className="form-grid">
          <label className="field">Name<input name="display_name" required /></label>
          <label className="field">FarmerID<input name="farmer_id" required /></label>
          <label className="field">Phone<input name="phone" /></label>
          <label className="field">Community<input name="community" /></label>
          <label className="field span-2">Region<input name="region" /></label>
        </div>
        <button type="submit">Save farmer</button>
      </form>
      <LoadNote loading={list.loading}>
        {farmers.length === 0 ? (
          <Empty title="No farmers yet" body="Register a farmer to attach farms and compliance records." />
        ) : (
          <div className="table-wrap card">
            <table>
              <thead><tr><th>Name</th><th>FarmerID</th><th>Community</th><th>Phone</th></tr></thead>
              <tbody>
                {farmers.map((farmer) => (
                  <tr key={farmer.id}>
                    <td>{farmer.display_name}</td>
                    <td>{farmer.farmer_id}</td>
                    <td>{farmer.community || farmer.region || '—'}</td>
                    <td>{farmer.phone || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </LoadNote>
    </>
  )
}

export function FarmsPage() {
  const farms = useLoad<Page<Farm>>('/api/v1/farms/')
  const fields = useLoad<Page<Field>>('/api/v1/fields/')
  const farmers = useLoad<Page<Farmer>>('/api/v1/farmers/')
  const [error, setError] = useState<string | null>(null)

  async function onFarm(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/farms/', 'POST', {
        farmer: data.get('farmer'),
        name: data.get('name'),
        latitude: data.get('latitude') || null,
        longitude: data.get('longitude') || null,
        region: data.get('region'),
      })
      form.reset()
      await farms.reload()
    }, setError)
  }

  async function onField(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      const raw = String(data.get('boundary') || '').trim()
      await sendJson('/api/v1/fields/', 'POST', {
        farm: data.get('farm'),
        name: data.get('name'),
        boundary: raw ? JSON.parse(raw) : null,
      })
      form.reset()
      await fields.reload()
      await farms.reload()
    }, setError)
  }

  async function onLandUse(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/land-use/', 'POST', {
        field: data.get('field'),
        year: Number(data.get('year')),
        use: data.get('use'),
      })
      form.reset()
      await fields.reload()
    }, setError)
  }

  const farmRows = results(farms.data)
  const fieldRows = results(fields.data)
  const farmerRows = results(farmers.data)

  return (
    <>
      <PageHead title="Farms and fields" lede="Field area is calculated from the boundary you save." />
      <Banner error={error || farms.error || fields.error} />
      <form className="card" onSubmit={(event) => void onFarm(event)}>
        <h2>Register a farm</h2>
        <div className="form-grid">
          <label className="field">Farmer
            <select name="farmer" required>
              <option value="">Select</option>
              {farmerRows.map((farmer) => (
                <option key={farmer.id} value={farmer.id}>{farmer.display_name}</option>
              ))}
            </select>
          </label>
          <label className="field">Name<input name="name" required /></label>
          <label className="field">Latitude<input name="latitude" placeholder="6.700000" /></label>
          <label className="field">Longitude<input name="longitude" placeholder="-1.600000" /></label>
          <label className="field span-2">Region<input name="region" /></label>
        </div>
        <button type="submit">Save farm</button>
      </form>
      <form className="card" onSubmit={(event) => void onField(event)}>
        <h2>Map a field</h2>
        <div className="form-grid">
          <label className="field">Farm
            <select name="farm" required>
              <option value="">Select</option>
              {farmRows.map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
            </select>
          </label>
          <label className="field">Name<input name="name" required /></label>
          <label className="field span-2">GeoJSON polygon
            <textarea name="boundary" placeholder='{"type":"Polygon","coordinates":[[[lon,lat],...]]}' />
          </label>
        </div>
        <button type="submit">Save field</button>
      </form>
      <LoadNote loading={farms.loading || fields.loading}>
        {farmRows.length === 0 ? (
          <Empty title="No farms yet" body="Register a farm after the farmer profile exists." />
        ) : (
          <div className="table-wrap card">
            <table>
              <thead><tr><th>Farm</th><th>Farmer</th><th>Fields</th><th>Mapped ha</th><th>Status</th></tr></thead>
              <tbody>
                {farmRows.map((farm) => (
                  <tr key={farm.id}>
                    <td>{farm.name}<div className="muted">{farm.code}</div></td>
                    <td>{farmerName(farmerRows, farm.farmer)}</td>
                    <td>{farm.field_count}</td>
                    <td>{num(farm.mapped_hectares)}</td>
                    <td><Badge value={farm.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {fieldRows.length > 0 ? (
          <div className="table-wrap card">
            <table>
              <thead><tr><th>Field</th><th>Boundary</th><th>Hectares</th><th>Missing land-use years</th></tr></thead>
              <tbody>
                {fieldRows.map((field) => (
                  <tr key={field.id}>
                    <td>{field.name}</td>
                    <td><BoundarySketch boundary={field.boundary} /></td>
                    <td>{num(field.area_hectares)}</td>
                    <td>{field.missing_land_use_years.join(', ') || 'Complete'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </LoadNote>
      <form className="card" onSubmit={(event) => void onLandUse(event)}>
        <h2>Land-use year</h2>
        <div className="form-grid">
          <label className="field">Field
            <select name="field" required>
              <option value="">Select</option>
              {fieldRows.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}
            </select>
          </label>
          <label className="field">Year<input name="year" type="number" required placeholder="2026" /></label>
          <label className="field span-2">Use<input name="use" required placeholder="Maize, fallow, forest…" /></label>
        </div>
        <button type="submit">Save land use</button>
      </form>
    </>
  )
}

function BoundarySketch({ boundary }: { boundary: Field['boundary'] }) {
  if (!boundary) return <span className="muted">No boundary</span>
  const ring = boundary.coordinates[0] ?? []
  if (ring.length < 3) return <span className="muted">No boundary</span>
  const lons = ring.map((point) => point[0] ?? 0)
  const lats = ring.map((point) => point[1] ?? 0)
  const minX = Math.min(...lons)
  const maxX = Math.max(...lons)
  const minY = Math.min(...lats)
  const maxY = Math.max(...lats)
  const width = maxX - minX || 1
  const height = maxY - minY || 1
  const pad = 8
  const points = ring
    .map(([lon, lat]) => {
      const x = pad + ((lon - minX) / width) * (100 - pad * 2)
      const y = pad + (1 - (lat - minY) / height) * (100 - pad * 2)
      return `${x},${y}`
    })
    .join(' ')
  return (
    <svg className="field-sketch" viewBox="0 0 100 100" role="img" aria-label="Field boundary">
      <polygon points={points} />
    </svg>
  )
}

export function CompliancePage({ role }: { role: string }) {
  const standards = useLoad<Page<Standard>>('/api/v1/standards/')
  const certifications = useLoad<Page<Certification>>('/api/v1/certifications/')
  const farmers = useLoad<Page<Farmer>>('/api/v1/farmers/')
  const [selected, setSelected] = useState<string>('')
  const detail = useLoad<Certification>(selected ? `/api/v1/certifications/${selected}/` : null)
  const [error, setError] = useState<string | null>(null)
  const canDecide = role === 'org_admin' || role === 'certification_officer'

  async function onOpen(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      const created = await sendJson<Certification>('/api/v1/certifications/', 'POST', {
        standard_id: data.get('standard_id'),
        farmer: data.get('farmer') || null,
      })
      setSelected(created.id)
      await certifications.reload()
    }, setError)
  }

  async function setState(id: string, state: string) {
    setError(null)
    try {
      await sendJson(`/api/v1/compliance-items/${id}/`, 'PATCH', { state })
      await detail.reload()
      await certifications.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the checklist.')
    }
  }

  async function onDecision(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson(`/api/v1/certifications/${selected}/decision/`, 'POST', {
        status: data.get('status'),
        certificate_number: data.get('certificate_number'),
        issued_on: data.get('issued_on') || null,
        expires_on: data.get('expires_on') || null,
        decision_notes: data.get('decision_notes'),
      })
      await detail.reload()
      await certifications.reload()
    }, setError)
  }

  const rows = results(certifications.data)
  const current = selected && detail.data && 'readiness' in detail.data ? detail.data : null

  return (
    <>
      <PageHead
        title="Compliance"
        lede="Checklists prepare a farm for a standard. Only a certification officer can record an official decision."
      />
      <Banner error={error || standards.error || certifications.error} />
      <form className="card" onSubmit={(event) => void onOpen(event)}>
        <h2>Open a checklist</h2>
        <div className="form-grid">
          <label className="field">Standard
            <select name="standard_id" required>
              <option value="">Select</option>
              {results(standards.data).map((standard) => (
                <option key={standard.id} value={standard.id}>{standard.code} — {standard.name}</option>
              ))}
            </select>
          </label>
          <label className="field">Farmer
            <select name="farmer">
              <option value="">Organization-wide</option>
              {results(farmers.data).map((farmer) => (
                <option key={farmer.id} value={farmer.id}>{farmer.display_name}</option>
              ))}
            </select>
          </label>
        </div>
        <button type="submit">Open checklist</button>
      </form>
      <div className="card">
        <h2>Cases</h2>
        {rows.length === 0 ? <p>No certification case is open.</p> : (
          <div className="stack">
            {rows.map((row) => (
              <button key={row.id} type="button" className="secondary" onClick={() => setSelected(row.id)}>
                {row.standard_code} · {row.readiness.readiness_percent ?? 'n/a'}% readiness · {row.status}
              </button>
            ))}
          </div>
        )}
      </div>
      {current ? (
        <article className="card">
          <h2>{current.status}</h2>
          <p className="muted">{current.readiness.message}</p>
          <p>
            Readiness {current.readiness.readiness_percent ?? 'not calculated'}%. Official certification:{' '}
            {current.readiness.is_official_certification ? 'yes' : 'no'}.
          </p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Requirement</th><th>State</th><th></th></tr></thead>
              <tbody>
                {(current.items ?? []).map((item) => (
                  <tr key={item.id}>
                    <td>{item.requirement.title}<div className="muted">Weight {item.requirement.weight}</div></td>
                    <td><Badge value={item.state} /></td>
                    <td className="actions">
                      <button type="button" className="secondary" onClick={() => void setState(item.id, 'declared')}>Declare</button>
                      {canDecide ? (
                        <button type="button" onClick={() => void setState(item.id, 'verified')}>Verify</button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {canDecide ? (
            <form onSubmit={(event) => void onDecision(event)} className="form-grid">
              <label className="field">Official status
                <select name="status" defaultValue="under_review">
                  <option value="under_review">Under review</option>
                  <option value="certified">Certified</option>
                  <option value="suspended">Suspended</option>
                  <option value="withdrawn">Withdrawn</option>
                </select>
              </label>
              <p className="muted span-2">
                Certified is an official decision and needs a certificate number. Readiness does not select it.
              </p>
              <label className="field">Certificate number<input name="certificate_number" /></label>
              <label className="field">Issued<input name="issued_on" type="date" /></label>
              <label className="field">Expires<input name="expires_on" type="date" /></label>
              <label className="field span-2">Notes<textarea name="decision_notes" /></label>
              <button type="submit">Record decision</button>
            </form>
          ) : (
            <p className="muted">Your role can declare records. It cannot mark the farm certified.</p>
          )}
        </article>
      ) : null}
    </>
  )
}

export function InventoryPage() {
  const products = useLoad<Page<Product>>('/api/v1/inputs/')
  const [error, setError] = useState<string | null>(null)

  async function onProduct(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/inputs/', 'POST', {
        name: data.get('name'),
        category: data.get('category'),
        unit: data.get('unit') || 'kg',
        reorder_level: data.get('reorder_level') || '0',
      })
      form.reset()
      await products.reload()
    }, setError)
  }

  async function onMove(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/stock-movements/', 'POST', {
        product: data.get('product'),
        kind: data.get('kind'),
        quantity: data.get('quantity'),
        occurred_on: data.get('occurred_on'),
        reference: data.get('reference'),
      })
      form.reset()
      await products.reload()
    }, setError)
  }

  const rows = results(products.data)
  return (
    <>
      <PageHead title="Inventory" lede="Stock is the sum of movements. A prohibited input cannot be issued." />
      <Banner error={error || products.error} />
      <form className="card" onSubmit={(event) => void onProduct(event)}>
        <h2>Add an input</h2>
        <div className="form-grid">
          <label className="field">Name<input name="name" required /></label>
          <label className="field">Category
            <select name="category" defaultValue="fertilizer">
              <option value="seed">Seed</option>
              <option value="fertilizer">Fertilizer</option>
              <option value="pesticide">Pesticide</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className="field">Unit<input name="unit" defaultValue="kg" /></label>
          <label className="field">Reorder level<input name="reorder_level" defaultValue="0" /></label>
        </div>
        <button type="submit">Save input</button>
      </form>
      <form className="card" onSubmit={(event) => void onMove(event)}>
        <h2>Stock movement</h2>
        <div className="form-grid">
          <label className="field">Input
            <select name="product" required>
              <option value="">Select</option>
              {rows.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
            </select>
          </label>
          <label className="field">Kind
            <select name="kind" defaultValue="in">
              <option value="in">In</option>
              <option value="out">Out</option>
              <option value="adjustment">Adjustment</option>
            </select>
          </label>
          <label className="field">Quantity<input name="quantity" required /></label>
          <label className="field">Date<input name="occurred_on" type="date" required /></label>
          <label className="field span-2">Reference<input name="reference" /></label>
        </div>
        <button type="submit">Save movement</button>
      </form>
      <LoadNote loading={products.loading}>
        {rows.length === 0 ? <Empty title="No inputs" body="Add seed, fertilizer, or other products." /> : (
          <div className="table-wrap card">
            <table>
              <thead><tr><th>Input</th><th>Category</th><th>On hand</th><th>Reorder</th></tr></thead>
              <tbody>
                {rows.map((product) => (
                  <tr key={product.id}>
                    <td>{product.name}</td>
                    <td>{product.category}</td>
                    <td>{num(product.on_hand)} {product.unit}</td>
                    <td>{num(product.reorder_level)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </LoadNote>
    </>
  )
}

export function ProductionPage() {
  const farms = useLoad<Page<Farm>>('/api/v1/farms/')
  const fields = useLoad<Page<Field>>('/api/v1/fields/')
  const harvests = useLoad<Page<Harvest>>('/api/v1/harvests/')
  const [error, setError] = useState<string | null>(null)

  async function onActivity(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/activities/', 'POST', {
        farm: data.get('farm'),
        kind: data.get('kind'),
        occurred_on: data.get('occurred_on'),
        notes: data.get('notes'),
      })
      form.reset()
    }, setError)
  }

  async function onHarvest(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/harvests/', 'POST', {
        farm: data.get('farm'),
        field: data.get('field'),
        harvested_on: data.get('harvested_on'),
        quantity_kg: data.get('quantity_kg'),
      })
      form.reset()
      await harvests.reload()
    }, setError)
  }

  return (
    <>
      <PageHead title="Production" lede="Harvest quantities are what yield and traceability calculate from." />
      <Banner error={error || harvests.error} />
      <form className="card" onSubmit={(event) => void onActivity(event)}>
        <h2>Farm activity</h2>
        <div className="form-grid">
          <label className="field">Farm
            <select name="farm" required>
              <option value="">Select</option>
              {results(farms.data).map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
            </select>
          </label>
          <label className="field">Kind
            <select name="kind" defaultValue="weeding">
              <option value="planting">Planting</option>
              <option value="weeding">Weeding</option>
              <option value="spraying">Spraying</option>
              <option value="fertilizing">Fertilizing</option>
              <option value="harvest">Harvest</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className="field">Date<input name="occurred_on" type="date" required /></label>
          <label className="field">Notes<input name="notes" /></label>
        </div>
        <button type="submit">Save activity</button>
      </form>
      <form className="card" onSubmit={(event) => void onHarvest(event)}>
        <h2>Harvest</h2>
        <div className="form-grid">
          <label className="field">Farm
            <select name="farm" required>
              <option value="">Select</option>
              {results(farms.data).map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
            </select>
          </label>
          <label className="field">Field
            <select name="field" required>
              <option value="">Select</option>
              {results(fields.data).map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}
            </select>
          </label>
          <label className="field">Date<input name="harvested_on" type="date" required /></label>
          <label className="field">Quantity kg<input name="quantity_kg" required /></label>
        </div>
        <button type="submit">Save harvest</button>
      </form>
      <LoadNote loading={harvests.loading}>
        {results(harvests.data).length === 0 ? (
          <Empty title="No harvests" body="Record a harvest before creating a traceability batch." />
        ) : (
          <div className="table-wrap card">
            <table>
              <thead><tr><th>Date</th><th>Kg</th></tr></thead>
              <tbody>
                {results(harvests.data).map((row) => (
                  <tr key={row.id}><td>{row.harvested_on}</td><td>{num(row.quantity_kg)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </LoadNote>
    </>
  )
}

export function TracePage() {
  const harvests = useLoad<Page<Harvest>>('/api/v1/harvests/')
  const batches = useLoad<Page<Batch>>('/api/v1/batches/')
  const [error, setError] = useState<string | null>(null)

  async function onBatch(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/batches/', 'POST', {
        product_name: data.get('product_name'),
        inputs: [{ harvest: data.get('harvest'), quantity_kg: data.get('quantity_kg') }],
      })
      form.reset()
      await batches.reload()
    }, setError)
  }

  async function onMove(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson(`/api/v1/batches/${data.get('batch')}/movements/`, 'POST', {
        kind: data.get('kind'),
        quantity_kg: data.get('quantity_kg') || '0',
        loss_kg: data.get('loss_kg') || '0',
        happened_on: data.get('happened_on'),
        location: data.get('location'),
      })
      form.reset()
      await batches.reload()
    }, setError)
  }

  async function downloadQr(batch: Batch) {
    const blob = await api<Blob>(`/api/v1/batches/${batch.id}/qr/`)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${batch.code}.png`
    link.click()
    URL.revokeObjectURL(url)
  }

  const rows = results(batches.data)
  return (
    <>
      <PageHead title="Traceability" lede="A batch keeps the harvest quantity, shipments, and loss in one balance." />
      <Banner error={error || batches.error} />
      <form className="card" onSubmit={(event) => void onBatch(event)}>
        <h2>Create a batch</h2>
        <div className="form-grid">
          <label className="field">Product<input name="product_name" required /></label>
          <label className="field">Harvest
            <select name="harvest" required>
              <option value="">Select</option>
              {results(harvests.data).map((harvest) => (
                <option key={harvest.id} value={harvest.id}>
                  {harvest.harvested_on} · {harvest.quantity_kg} kg
                </option>
              ))}
            </select>
          </label>
          <label className="field">Quantity kg<input name="quantity_kg" required /></label>
        </div>
        <button type="submit">Create batch</button>
      </form>
      <form className="card" onSubmit={(event) => void onMove(event)}>
        <h2>Record a movement</h2>
        <div className="form-grid">
          <label className="field">Batch
            <select name="batch" required>
              <option value="">Select</option>
              {rows.map((batch) => <option key={batch.id} value={batch.id}>{batch.code}</option>)}
            </select>
          </label>
          <label className="field">Kind
            <select name="kind" defaultValue="ship">
              <option value="store">Store</option>
              <option value="transport">Transport</option>
              <option value="process">Process</option>
              <option value="ship">Ship</option>
            </select>
          </label>
          <label className="field">Quantity kg<input name="quantity_kg" /></label>
          <label className="field">Loss kg<input name="loss_kg" /></label>
          <label className="field">Date<input name="happened_on" type="date" required /></label>
          <label className="field">Location<input name="location" /></label>
        </div>
        <button type="submit">Save movement</button>
      </form>
      <LoadNote loading={batches.loading}>
        {rows.length === 0 ? <Empty title="No batches" body="Create a batch from a recorded harvest." /> : (
          <div className="table-wrap card">
            <table>
              <thead><tr><th>Code</th><th>Product</th><th>Sourced</th><th>Remaining</th><th></th></tr></thead>
              <tbody>
                {rows.map((batch) => (
                  <tr key={batch.id}>
                    <td>{batch.code}<div className="muted">{batch.public_code}</div></td>
                    <td>{batch.product_name}</td>
                    <td>{num(batch.balance.sourced_kg)}</td>
                    <td>{num(batch.balance.remaining_kg)}</td>
                    <td><button type="button" className="secondary" onClick={() => void downloadQr(batch)}>QR</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </LoadNote>
    </>
  )
}

type Session = { id: string; title: string; held_on: string; trainer_name: string }
type Inspection = { id: string; farm_name: string; scheduled_for: string; status: string }

export function InspectionsPage() {
  const farms = useLoad<Page<Farm>>('/api/v1/farms/')
  const inspections = useLoad<Page<Inspection>>('/api/v1/inspections/')
  const [error, setError] = useState<string | null>(null)

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      const when = String(data.get('scheduled_for') || '')
      await sendJson('/api/v1/inspections/', 'POST', {
        farm: data.get('farm'),
        scheduled_for: when.length === 16 ? `${when}:00` : when,
        checks: ['Boundaries match the map', 'Inputs on the farm are recorded', 'Harvest records are available'],
      })
      form.reset()
      await inspections.reload()
    }, setError)
  }

  return (
    <>
      <PageHead title="Inspections" lede="Schedule a visit and keep the checklist with the farm." />
      <Banner error={error || inspections.error} />
      <form className="card" onSubmit={(event) => void onCreate(event)}>
        <div className="form-grid">
          <label className="field">Farm
            <select name="farm" required>
              <option value="">Select</option>
              {results(farms.data).map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
            </select>
          </label>
          <label className="field">When<input name="scheduled_for" type="datetime-local" required /></label>
        </div>
        <button type="submit">Schedule inspection</button>
      </form>
      <LoadNote loading={inspections.loading}>
        {results(inspections.data).length === 0 ? <Empty title="No inspections" body="Scheduled visits will show on the dashboard." /> : (
          <div className="table-wrap card">
            <table>
              <thead><tr><th>When</th><th>Farm</th><th>Status</th></tr></thead>
              <tbody>
                {results(inspections.data).map((row) => (
                  <tr key={row.id}>
                    <td>{row.scheduled_for}</td><td>{row.farm_name}</td><td><Badge value={row.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </LoadNote>
    </>
  )
}

export function TrainingPage() {
  const sessions = useLoad<Page<Session>>('/api/v1/training-sessions/')
  const farmers = useLoad<Page<Farmer>>('/api/v1/farmers/')
  const [error, setError] = useState<string | null>(null)

  async function onSession(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/training-sessions/', 'POST', {
        title: data.get('title'),
        held_on: data.get('held_on'),
        trainer_name: data.get('trainer_name'),
        location: data.get('location'),
      })
      form.reset()
      await sessions.reload()
    }, setError)
  }

  async function onAttend(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/attendance/', 'POST', {
        session: data.get('session'),
        farmer: data.get('farmer'),
        present: true,
      })
      form.reset()
    }, setError)
  }

  return (
    <>
      <PageHead title="Training" lede="Attendance is the farmer's training history." />
      <Banner error={error || sessions.error} />
      <form className="card" onSubmit={(event) => void onSession(event)}>
        <h2>Session</h2>
        <div className="form-grid">
          <label className="field">Title<input name="title" required /></label>
          <label className="field">Date<input name="held_on" type="date" required /></label>
          <label className="field">Trainer<input name="trainer_name" /></label>
          <label className="field">Location<input name="location" /></label>
        </div>
        <button type="submit">Save session</button>
      </form>
      <form className="card" onSubmit={(event) => void onAttend(event)}>
        <h2>Attendance</h2>
        <div className="form-grid">
          <label className="field">Session
            <select name="session" required>
              <option value="">Select</option>
              {results(sessions.data).map((session) => (
                <option key={session.id} value={session.id}>{session.title}</option>
              ))}
            </select>
          </label>
          <label className="field">Farmer
            <select name="farmer" required>
              <option value="">Select</option>
              {results(farmers.data).map((farmer) => (
                <option key={farmer.id} value={farmer.id}>{farmer.display_name}</option>
              ))}
            </select>
          </label>
        </div>
        <button type="submit">Mark present</button>
      </form>
    </>
  )
}

export function ReportsPage() {
  const [error, setError] = useState<string | null>(null)
  const kinds = [
    ['farms', 'Farms'],
    ['production', 'Production'],
    ['yield', 'Yield'],
    ['inventory', 'Inventory'],
    ['compliance', 'Compliance'],
  ] as const

  async function download(kind: string) {
    setError(null)
    try {
      const blob = await api<Blob>(`/api/v1/reports/${kind}/?format=csv`)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${kind}-report.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not download the report.')
    }
  }

  return (
    <>
      <PageHead title="Reports" lede="Downloads use the same records as the tables. They are not estimates." />
      <Banner error={error} />
      <div className="actions">
        {kinds.map(([kind, label]) => (
          <button key={kind} type="button" onClick={() => void download(kind)}>{label} CSV</button>
        ))}
      </div>
    </>
  )
}

export function AssistantPage() {
  const [error, setError] = useState<string | null>(null)
  const [answer, setAnswer] = useState<string>('')
  const [statements, setStatements] = useState<{ kind: string; text: string }[]>([])
  const [narrative, setNarrative] = useState<string>('')

  async function onAsk(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      const result = await sendJson<{
        answer: string
        narrative: string | null
        statements: { kind: string; text: string }[]
      }>('/api/v1/assistant/', 'POST', { question: data.get('question') })
      setAnswer(result.answer)
      setStatements(result.statements)
      setNarrative(result.narrative ?? '')
    }, setError)
  }

  return (
    <>
      <PageHead
        title="Farm assistant"
        lede="Answers are built from your records. Missing data stays missing. A language model is used only when an API key is configured."
      />
      <Banner error={error} />
      <form className="card" onSubmit={(event) => void onAsk(event)}>
        <label className="field">Question
          <textarea name="question" required placeholder="What compliance evidence is missing?" />
        </label>
        <button type="submit">Ask</button>
      </form>
      {answer ? (
        <article className="card">
          <h2>From your records</h2>
          <p>{answer}</p>
          <div className="stack">
            {statements.map((row) => (
              <p key={`${row.kind}-${row.text}`}><Badge value={row.kind} /> {row.text}</p>
            ))}
          </div>
          {narrative ? (
            <>
              <h2>Model summary</h2>
              <p>{narrative}</p>
            </>
          ) : null}
        </article>
      ) : null}
    </>
  )
}

type Member = { id: string; email: string; first_name: string; role: string; is_active: boolean }

export function SettingsPage({
  role,
  onRefresh,
}: {
  role: string
  onRefresh: () => Promise<void>
}) {
  const { me } = useAuth()
  const members = useLoad<Page<Member>>(role === 'org_admin' ? '/api/v1/members/' : null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState('')

  async function onProfile(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/auth/me/', 'PATCH', {
        first_name: data.get('first_name'),
        last_name: data.get('last_name'),
        phone: data.get('phone'),
      })
      await onRefresh()
      setNotice('Profile saved.')
    }, setError)
  }

  async function onMember(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    await submitJson(event, async () => {
      const data = new FormData(form)
      await sendJson('/api/v1/members/', 'POST', {
        email: data.get('email'),
        password: data.get('password'),
        role: data.get('role'),
        first_name: data.get('first_name'),
        farmer_id: data.get('farmer_id'),
        display_name: data.get('display_name'),
      })
      form.reset()
      await members.reload()
    }, setError)
  }

  return (
    <>
      <PageHead title="Settings" lede="Organization accounts are created here. Farmer self-signup is not open." />
      <Banner error={error} />
      {notice ? <p className="alert">{notice}</p> : null}
      <form
        className="card"
        key={`${me?.email ?? ''}:${me?.first_name ?? ''}:${me?.last_name ?? ''}:${me?.phone ?? ''}`}
        onSubmit={(event) => void onProfile(event)}
      >
        <h2>Your profile</h2>
        <p className="muted">{me?.email}</p>
        <div className="form-grid">
          <label className="field">First name<input name="first_name" defaultValue={me?.first_name ?? ''} /></label>
          <label className="field">Last name<input name="last_name" defaultValue={me?.last_name ?? ''} /></label>
          <label className="field span-2">Phone<input name="phone" defaultValue={me?.phone ?? ''} /></label>
        </div>
        <button type="submit">Save profile</button>
      </form>
      {role === 'org_admin' ? (
        <>
          <form className="card" onSubmit={(event) => void onMember(event)}>
            <h2>Add an account</h2>
            <div className="form-grid">
              <label className="field">Email<input name="email" type="email" required /></label>
              <label className="field">Password<input name="password" type="password" required /></label>
              <label className="field">First name<input name="first_name" /></label>
              <label className="field">Role
                <select name="role" defaultValue="field_officer">
                  <option value="org_admin">Organization admin</option>
                  <option value="field_officer">Field officer</option>
                  <option value="manager">Farm manager</option>
                  <option value="farmer">Farmer</option>
                  <option value="inspector">Inspector</option>
                  <option value="certification_officer">Certification officer</option>
                </select>
              </label>
              <label className="field">FarmerID<input name="farmer_id" /></label>
              <label className="field">Display name<input name="display_name" /></label>
            </div>
            <button type="submit">Create account</button>
          </form>
          <LoadNote loading={members.loading}>
            <div className="table-wrap card">
              <table>
                <thead><tr><th>Email</th><th>Role</th><th>Active</th></tr></thead>
                <tbody>
                  {results(members.data).map((member) => (
                    <tr key={member.id}>
                      <td>{member.email}</td>
                      <td>{member.role}</td>
                      <td>{member.is_active ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </LoadNote>
        </>
      ) : null}
    </>
  )
}
