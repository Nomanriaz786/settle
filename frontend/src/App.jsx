/** Settle dashboard: the open chargebacks on the left, the selected case and Settle's recommendation on the right. */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { AgGridReact } from 'ag-grid-react'
import { themeQuartz } from 'ag-grid-community'
import { api } from './api'

const REASONS = {
  fraud: 'Cardholder says they did not make this purchase',
  product_not_received: 'Customer says the order never arrived',
  product_unsatisfactory: 'Customer says the item was not as described',
  duplicate: 'Customer says they were charged twice',
  credit_not_processed: 'Customer says a refund was never issued',
  cancelled_recurring_transaction: 'Customer says they cancelled the subscription',
}
const SHORT_REASONS = {
  fraud: 'Not authorised', product_not_received: 'Not received', product_unsatisfactory: 'Not as described',
  duplicate: 'Charged twice', credit_not_processed: 'Refund missing', cancelled_recurring_transaction: 'Cancelled plan',
}
const STEP_LABELS = {
  get_order: 'Pulled the order and the Braintree payment record',
  check_evidence: 'Checked the evidence card networks expect for this reason',
  get_customer_history: "Looked up the customer's earlier orders",
}
const SCENARIOS = [
  { id: 'friendly_fraud', label: 'Repeat customer disputes a delivered order', amount: 129 },
  { id: 'stolen_card', label: 'Order shipped to a stranger, card was stolen', amount: 389 },
  { id: 'forgotten_subscription', label: 'Subscriber forgot what they signed up for', amount: 49 },
]

const STATUS = { disputed: 'Evidence sent', accepted: 'Accepted', auto_accepted: 'Accepted', won: 'Won', lost: 'Lost', expired: 'Expired', under_review: 'Under review' }
const money = (v) => `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const daysLeft = (date) => (date ? Math.ceil((new Date(date) - new Date()) / 86400000) : null)
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
const shortDate = (d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

const gridTheme = themeQuartz.withParams({
  fontFamily: 'inherit', fontSize: 14, headerFontSize: 13, headerFontWeight: 600,
  foregroundColor: '#1C2B2A', backgroundColor: '#FFFFFF', headerBackgroundColor: '#FFFFFF',
  borderColor: '#D3DCD9', rowBorder: { color: '#E6ECEA' }, wrapperBorderRadius: 10,
  selectedRowBackgroundColor: '#E3EFEB', rowHoverColor: '#F1F5F4', accentColor: '#1F6F5C',
  rowHeight: 58, headerHeight: 42, spacing: 7,
})

function CustomerCell({ data }) {
  return (
    <div className="cell-customer">
      <strong>{data.customer_name || 'Unknown customer'}</strong>
      <span>{data.items?.join(', ') || data.transaction_id}</span>
    </div>
  )
}

function ReplyCell({ data }) {
  if (data.status !== 'open') return <span className="muted">{STATUS[data.status] || data.status}</span>
  const d = daysLeft(data.reply_by)
  return <span className={d <= 2 ? 'urgent' : ''}>{d <= 0 ? 'Due today' : `${plural(d, 'day')} left`}</span>
}

function VerdictCell({ data }) {
  if (!data.verdict) return <span className="muted">{data.status === 'open' ? 'Not reviewed' : ''}</span>
  return <span className={`pill ${data.verdict}`}>{data.verdict === 'fight' ? 'Fight' : 'Accept'} {Math.round(data.confidence * 100)}%</span>
}

const columns = [
  { headerName: 'Customer', field: 'customer_name', cellRenderer: CustomerCell, flex: 2, minWidth: 200 },
  { headerName: 'Amount', field: 'amount', valueFormatter: (p) => money(p.value), comparator: (a, b) => a - b,
    type: 'rightAligned', width: 110, cellClass: 'num' },
  { headerName: 'Reason', field: 'reason', valueFormatter: (p) => SHORT_REASONS[p.value] || p.value, flex: 1, minWidth: 130 },
  { headerName: 'Reply by', field: 'reply_by', cellRenderer: ReplyCell, width: 130 },
  { headerName: 'Settle says', field: 'verdict', cellRenderer: VerdictCell, width: 140 },
]

function DeadlineBar({ received, replyBy }) {
  const start = received ? new Date(received) : new Date(new Date(replyBy) - 7 * 86400000)
  const used = Math.min(1, Math.max(0, (new Date() - start) / (new Date(replyBy) - start)))
  const left = daysLeft(replyBy)
  return (
    <div className="deadline">
      <div className="deadline-track" aria-hidden="true">
        <div className={`deadline-fill ${left <= 2 ? 'urgent' : ''}`} style={{ width: `${used * 100}%` }} />
      </div>
      <div className="deadline-labels">
        <span>Opened {shortDate(start)}</span>
        <strong className={left <= 2 ? 'urgent' : ''}>
          {left <= 0 ? 'Reply due today' : `Reply within ${plural(left, 'day')}, by ${shortDate(replyBy)}`}
        </strong>
      </div>
    </div>
  )
}

function OrderFacts({ order }) {
  if (!order) return <p className="muted">This payment has no order record in the shop.</p>
  const rows = [
    ['Items', order.items?.join(', ')],
    ['Billed to', order.billing_address],
    ['Shipped to', order.shipping_address],
    ['Delivery', order.delivered_at
      ? `${order.carrier} ${order.tracking_number}, delivered ${shortDate(order.delivered_at)}${order.signature ? ', signed for' : ''}`
      : 'No delivery confirmation'],
    ['Earlier orders', order.prior_orders ? plural(order.prior_orders, 'order') : 'None, first order'],
  ]
  return (
    <>
      <dl className="facts">{rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v || 'Not recorded'}</dd></div>)}</dl>
      {order.messages?.map((m) => <blockquote key={m}>{m}</blockquote>)}
    </>
  )
}

function Checklist({ items, strength }) {
  return (
    <>
      <ul className="checklist">
        {items.map((i) => (
          <li key={i.item} className={i.ok ? 'ok' : 'missing'}>
            <span className="mark" aria-hidden="true">{i.ok ? '✓' : '✕'}</span>
            {i.item}<span className="sr-only">{i.ok ? ', found' : ', missing'}</span>
          </li>
        ))}
      </ul>
      <p className="muted small">{Math.round(strength * items.length)} of {items.length} found</p>
    </>
  )
}

function Recommendation({ dispute, onDone, notify }) {
  const { analysis, status } = dispute
  const [draft, setDraft] = useState(analysis?.evidence_text || '')
  const [busy, setBusy] = useState(null)
  const open = status === 'open'

  const run = async (kind, fn, success) => {
    setBusy(kind)
    try { await fn(); notify(success); await onDone() } catch (e) { notify(e.message, true) } finally { setBusy(null) }
  }
  const review = () => run('review', () => api.analyze(dispute.id), 'Review finished')

  if (!analysis || busy === 'review') {
    return (
      <section className="block">
        <h3>Settle's recommendation</h3>
        <p className="muted">Settle reads the order, checks the evidence and tells you whether this dispute is worth fighting. Nothing is sent until you approve it.</p>
        <button className="primary" onClick={review} disabled={!!busy || !open}>
          {busy === 'review' ? 'Reviewing the case...' : 'Review this case'}
        </button>
        {busy === 'review' && <p className="working" aria-live="polite"><span className="pulse" />Reading the order, the payment and the evidence</p>}
      </section>
    )
  }

  const fight = analysis.verdict === 'fight'
  return (
    <section className="block">
      <div className={`ruling ${analysis.verdict}`}>
        <span className="ruling-label">Settle recommends</span>
        <strong>{fight ? 'Fight this dispute' : 'Accept this dispute'}</strong>
        <span className="ruling-odds num">
          {fight ? 'Estimated chance of winning' : 'Estimated chance if fought'}: {Math.round(analysis.confidence * 100)}%
        </span>
      </div>
      <ul className="reasons">{analysis.reasons.map((r) => <li key={r}>{r}</li>)}</ul>

      <h4>What Settle did</h4>
      <ol className="trail">
        {analysis.steps.map((s, i) => <li key={i}>{STEP_LABELS[s.tool] || s.tool}</li>)}
        <li>Wrote the recommendation{fight ? ' and drafted your evidence' : ''}</li>
      </ol>

      {analysis.submitted ? (
        <p className="done" role="status">Evidence submitted to Braintree. The card network decides, usually within a few weeks.</p>
      ) : !open ? (
        <p className="muted">This dispute is closed ({(STATUS[status] || status).toLowerCase()}), so there is nothing left to do.</p>
      ) : fight ? (
        <>
          <label className="draft-label" htmlFor="draft">Your evidence for the card network. Edit anything before you submit.</label>
          <textarea id="draft" value={draft} onChange={(e) => setDraft(e.target.value)} rows={9} maxLength={4000} />
          <div className="actions">
            <button className="primary" disabled={!!busy || !draft.trim()}
              onClick={() => run('submit', () => api.approve(dispute.id, draft), 'Evidence submitted to Braintree')}>
              {busy === 'submit' ? 'Submitting...' : 'Submit evidence to Braintree'}
            </button>
            <button className="quiet" disabled={!!busy} onClick={review}>Review again</button>
          </div>
        </>
      ) : (
        <div className="actions">
          <button className="primary accept" disabled={!!busy}
            onClick={() => window.confirm(`Accept this chargeback? ${money(dispute.amount)} stays with the cardholder.`) &&
              run('accept', () => api.accept(dispute.id), 'Chargeback accepted')}>
            {busy === 'accept' ? 'Accepting...' : `Accept the ${money(dispute.amount)} chargeback`}
          </button>
          <button className="quiet" disabled={!!busy} onClick={review}>Review again</button>
        </div>
      )}
    </section>
  )
}

function CaseFile({ id, onChanged, notify }) {
  const [dispute, setDispute] = useState(null)
  const load = useCallback(() => api.dispute(id).then(setDispute).catch((e) => notify(e.message, true)), [id, notify])
  useEffect(() => { setDispute(null); load() }, [load])

  if (!dispute) return <aside className="case"><p className="muted">Loading the case...</p></aside>
  const refresh = async () => { await load(); onChanged() }
  return (
    <aside className="case">
      <header className="case-head">
        <div>
          <h2>{dispute.order?.customer_name || 'Unknown customer'}</h2>
          <p>{REASONS[dispute.reason] || dispute.reason}</p>
        </div>
        <span className="case-amount num">{money(dispute.amount)}</span>
      </header>
      {dispute.status === 'open' && dispute.reply_by && <DeadlineBar received={dispute.received} replyBy={dispute.reply_by} />}
      <section className="block"><h3>The order</h3><OrderFacts order={dispute.order} /></section>
      <section className="block"><h3>Evidence on file</h3><Checklist items={dispute.checklist} strength={dispute.strength} /></section>
      <Recommendation key={`${dispute.id}-${dispute.analysis?.evidence_text ?? ''}-${dispute.status}`}
        dispute={dispute} onDone={refresh} notify={notify} />
      <p className="case-id muted small">Braintree dispute {dispute.id}, payment {dispute.transaction_id}</p>
    </aside>
  )
}

export default function App() {
  const [rows, setRows] = useState(null)
  const [selected, setSelected] = useState(null)
  const [toast, setToast] = useState(null)
  const [menu, setMenu] = useState(false)
  const [simulating, setSimulating] = useState(false)

  const notify = useCallback((text, error = false) => {
    setToast({ text, error })
    setTimeout(() => setToast(null), 4500)
  }, [])
  const load = useCallback(() => api.disputes()
    .then((r) => { setRows(r); return r })
    .catch((e) => { notify(e.message, true); setRows([]); return [] }), [notify])
  useEffect(() => { load() }, [load])

  const open = useMemo(() => (rows || []).filter((r) => r.status === 'open'), [rows])
  // open cases first, the most urgent at the top
  const sorted = useMemo(() => [...(rows || [])].sort((a, b) =>
    (a.status !== 'open') - (b.status !== 'open') || String(a.reply_by).localeCompare(String(b.reply_by))), [rows])
  const atRisk = open.reduce((s, r) => s + Number(r.amount), 0)
  const nextDue = Math.min(...open.map((r) => daysLeft(r.reply_by)).filter((d) => d !== null))

  const simulate = async (scenario) => {
    setMenu(false)
    setSimulating(true)
    try {
      const { transaction_id } = await api.simulate(scenario)
      for (let i = 0; i < 12; i++) {
        const found = (await load()).find((r) => r.transaction_id === transaction_id)
        if (found) { setSelected(found.id); notify('New chargeback received from Braintree'); return }
        await new Promise((r) => setTimeout(r, 1500))
      }
      notify('Braintree has not raised the dispute yet. Refresh in a minute.', true)
    } catch (e) { notify(e.message, true) } finally { setSimulating(false) }
  }

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <span className="logo" aria-hidden="true" />
          <div><strong>Settle</strong><span>Kiln &amp; Co. ceramics</span></div>
        </div>
        <div className="sim">
          <button className="quiet" onClick={() => setMenu(!menu)} aria-expanded={menu} disabled={simulating}>
            {simulating ? 'Waiting for Braintree...' : 'Simulate a chargeback'}
          </button>
          {menu && (
            <ul className="sim-menu" role="menu">
              {SCENARIOS.map((s) => (
                <li key={s.id} role="none">
                  <button role="menuitem" onClick={() => simulate(s.id)}>{s.label}<span className="num">{money(s.amount)}</span></button>
                </li>
              ))}
              <li role="none" className="sim-note">Makes a real test payment and dispute in the Braintree sandbox.</li>
            </ul>
          )}
        </div>
      </header>

      <main>
        <section className="summary" aria-live="polite">
          {rows === null ? <h1>Loading your disputes...</h1> : open.length === 0 ? (
            <h1>No open disputes. Simulate a chargeback to see how Settle handles one.</h1>
          ) : (
            <h1>
              <span className="num">{money(atRisk)}</span> is at risk across {plural(open.length, 'open dispute')}.{' '}
              <span className="sub">{nextDue <= 0 ? 'A reply is due today.' : `The next reply is due in ${plural(nextDue, 'day')}.`}</span>
            </h1>
          )}
          <p>Settle reviews each chargeback, tells you which ones are worth fighting and drafts the evidence. You approve every submission.</p>
        </section>

        <div className="desk">
          <div className="grid-wrap">
            <AgGridReact
              theme={gridTheme} rowData={sorted} columnDefs={columns} getRowId={(p) => p.data.id}
              rowSelection={{ mode: 'singleRow', checkboxes: false, enableClickSelection: true }}
              onRowClicked={(e) => setSelected(e.data.id)} loading={rows === null} domLayout="autoHeight"
              defaultColDef={{ sortable: true, resizable: false, suppressMovable: true }}
            />
          </div>
          {selected ? <CaseFile id={selected} onChanged={load} notify={notify} /> : (
            <aside className="case empty"><p>Select a dispute to open the case and see what Settle recommends.</p></aside>
          )}
        </div>
      </main>

      {toast && <div className={`toast ${toast.error ? 'error' : ''}`} role="status">{toast.text}</div>}
    </div>
  )
}
