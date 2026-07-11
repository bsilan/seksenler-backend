import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from './api.js'

const POLL_MS = 2000
const SESSION_KEY = 'seksenler_session'

const ROLE_DESC = {
  Demokrat: '5 Demokrasi Reformu geçir ya da Kenan Evren’i bul. Kimseye güvenme — herkes "Demokratım" diyor.',
  Darbeci: 'Sıkıyönetim Kararlarını gizlice geçir. Kenan Evren’i koru; kimliğin açığa çıkmasın.',
  'Kenan Evren': 'Kimliğin en büyük sır. 3 Sıkıyönetim’den sonra Başbakan seçilirsen darbe tamamlanır.',
}
const POWER_TITLES = {
  investigate: 'SORGULAMA — bir vatandaşın parti üyeliğini gizlice öğren',
  peek: 'GÖZETLEME — destenin üstündeki 3 kartı gizlice gör',
  special_election: 'ÖZEL SEÇİM — sıradaki Cumhurbaşkanı’nı sen ata',
  execute: 'İNFAZ — bir oyuncuyu meclisten sonsuza dek çıkar',
}

function loadSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY)) } catch { return null }
}

export default function App() {
  const [session, setSession] = useState(loadSession)
  const [st, setSt] = useState(null)
  const [role, setRole] = useState(null)
  const [error, setError] = useState(null)
  const [priv, setPriv] = useState(null) // sorgu sonucu / gözetlenen kartlar (yalnızca bende)
  const stRef = useRef(null)

  const saveSession = (s) => {
    setSession(s)
    if (s) localStorage.setItem(SESSION_KEY, JSON.stringify(s))
    else localStorage.removeItem(SESSION_KEY)
  }

  const refresh = useCallback(async () => {
    const s = session
    if (!s) return
    try {
      const data = await api.getState(s.gameId, s.playerId)
      stRef.current = data
      setSt(data)
      setError(null)
    } catch (e) {
      if (e.status === 404) { // oda silinmiş (sunucu yeniden başlamış olabilir)
        saveSession(null); setSt(null); setRole(null)
      } else {
        setError(e.message)
      }
    }
  }, [session])

  useEffect(() => {
    if (!session) return
    refresh()
    const t = setInterval(refresh, POLL_MS)
    return () => clearInterval(t)
  }, [session, refresh])

  useEffect(() => {
    if (!session || !st || role) return
    if (st.phase !== 'lobby') {
      api.getMyRole(session.gameId, session.playerId).then(setRole).catch(() => {})
    }
  }, [session, st, role])

  const act = async (fn) => {
    setError(null)
    try { await fn(); await refresh() }
    catch (e) { setError(e.message) }
  }

  if (!session) {
    return <Join onDone={saveSession} />
  }
  if (!st) {
    return (
      <div className="app">
        <Masthead mini />
        <p className="hint">Bağlanılıyor…</p>
        {error && <div className="error">{error}</div>}
      </div>
    )
  }

  const me = st.players.find((p) => p.nickname === session.nickname)
  const amAlive = me ? me.alive : true

  return (
    <div className="app">
      {st.phase === 'lobby' && (
        <Lobby st={st} session={session} onStart={() => act(() => api.startGame(session.gameId))} />
      )}
      {st.phase === 'game_over' && (
        <GameOver st={st} onNew={() => { saveSession(null); setSt(null); setRole(null); setPriv(null) }} />
      )}
      {st.phase !== 'lobby' && st.phase !== 'game_over' && (
        <>
          <PhaseBanner st={st} session={session} amAlive={amAlive} />
          {!amAlive && <div className="error">İnfaz edildiniz. Oyunu sessizce izliyorsunuz — konuşmak yasak!</div>}
          {priv && <PrivateResult priv={priv} onClose={() => setPriv(null)} />}
          {amAlive && !priv && (
            <ActionPanel st={st} session={session} act={act} setPriv={setPriv} />
          )}
          <Board st={st} />
          {role && <RoleDossier role={role} nickname={session.nickname} />}
        </>
      )}
      {error && <div className="error">{error}</div>}
    </div>
  )
}

function Masthead({ mini, eyebrow = 'Fevkalâde Nüsha · Tek Kuruş' }) {
  return (
    <header className={'masthead' + (mini ? ' mini' : '')}>
      <div className="eyebrow">{eyebrow}</div>
      <h1>SEKSENLER</h1>
      {!mini && (
        <div className="dateline"><span>12 Eylül 1980, Cuma</span><span>Sayı: 1</span></div>
      )}
    </header>
  )
}

/* ============ 1 · GİRİŞ ============ */
function Join({ onDone }) {
  const [nickname, setNickname] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const go = async (fn) => {
    if (!nickname.trim()) { setError('Önce takma adını yaz.'); return }
    setBusy(true); setError(null)
    try { await fn() } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const create = () => go(async () => {
    const r = await api.createGame(nickname.trim())
    onDone({ gameId: r.game_id, playerId: r.player_id, nickname: nickname.trim() })
  })
  const join = () => go(async () => {
    if (!code.trim()) { throw new Error('Oda kodunu yaz.') }
    const gid = code.trim().toLowerCase()
    const r = await api.joinGame(gid, nickname.trim())
    onDone({ gameId: gid, playerId: r.player_id, nickname: nickname.trim() })
  })

  return (
    <div className="app">
      <Masthead />
      <p className="lede">
        Meclis koridorlarında fısıltılar dolaşıyor. Kimi <em>darbe</em> peşinde, kimi demokrasiyi
        savunuyor. Kimin kim olduğunu bilmiyorsunuz.
      </p>
      <div className="field">
        <label htmlFor="nick">Takma Adınız</label>
        <input id="nick" value={nickname} onChange={(e) => setNickname(e.target.value)} maxLength={16} />
      </div>
      <button className="btn red" onClick={create} disabled={busy}>Oda Kur</button>
      <div className="or">VEYA</div>
      <div className="field">
        <label htmlFor="code">Oda Kodu</label>
        <input id="code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="ör. 7f3a21b9" />
      </div>
      <button className="btn ghost" onClick={join} disabled={busy}>Odaya Katıl</button>
      {error && <div className="error">{error}</div>}
    </div>
  )
}

/* ============ 2 · LOBİ ============ */
function Lobby({ st, session, onStart }) {
  const me = st.players.find((p) => p.nickname === session.nickname)
  const isCreator = me && me.is_creator
  const n = st.players.length
  const ready = n >= 5
  return (
    <>
      <Masthead mini eyebrow="Toplantı Salonu" />
      <div className="roomcode">
        <div className="cap">ODA KODU — ARKADAŞLARINA SÖYLE</div>
        <div className="code">{session.gameId.toUpperCase()}</div>
      </div>
      <div className="clip">
        <h3>Katılanlar</h3>
        <ul className="plist">
          {st.players.map((p, i) => (
            <li key={p.nickname}>
              <span className="no">{i + 1}.</span> {p.nickname}
              {p.is_creator && <span className="tag k">KURUCU</span>}
            </li>
          ))}
        </ul>
      </div>
      <p className="counter">
        <b>{n}</b>/10 oyuncu — {ready ? 'oyun başlayabilir' : `en az ${5 - n} kişi daha gerek`}
      </p>
      {isCreator ? (
        <button className="btn red" onClick={onStart} disabled={!ready}>Oyunu Başlat</button>
      ) : (
        <p className="hint">Kurucunun oyunu başlatması bekleniyor…</p>
      )}
    </>
  )
}

/* ============ 3 · ROL DOSYASI ============ */
function RoleDossier({ role, nickname }) {
  const [show, setShow] = useState(false)
  const cls = role.role === 'Demokrat' ? 'demokrat' : 'darbeci'
  return (
    <div className="dossier">
      <span className="stamp">Çok Gizli</span>
      <div style={{ fontFamily: "'Courier New',monospace", fontSize: 10, marginTop: 8, letterSpacing: '.15em', color: 'var(--ink-soft)' }}>
        SİCİL DOSYASI — {nickname.toUpperCase()}
      </div>
      <button
        className="btn holdbtn"
        onPointerDown={(e) => { e.preventDefault(); setShow(true) }}
        onPointerUp={() => setShow(false)}
        onPointerLeave={() => setShow(false)}
        onPointerCancel={() => setShow(false)}
        onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') setShow(true) }}
        onKeyUp={() => setShow(false)}
      >
        Basılı Tut ve Gör
      </button>
      <div className={'rolecard ' + cls + (show ? ' show' : '')}>
        <div className="rname">{role.role.toUpperCase()}</div>
        <p className="rdesc">{ROLE_DESC[role.role]}</p>
        <div className="mates">
          {role.teammates && role.teammates.length
            ? 'Yoldaşların: ' + role.teammates.join(', ')
            : 'Kimseyi tanımıyorsun. Gözünü dört aç.'}
        </div>
      </div>
    </div>
  )
}

/* ============ FAZ BANNER'I ============ */
function PhaseBanner({ st, session, amAlive }) {
  const iAmPresident = st.is_president
  const iAmChancellor = st.is_chancellor
  let text
  switch (st.phase) {
    case 'nomination':
      text = iAmPresident
        ? <>CUMHURBAŞKANI SİZSİNİZ — <b>BAŞBAKAN ADAYI</b> SEÇİN</>
        : <><b>{st.president}</b> BAŞBAKAN ADAYI GÖSTERİYOR…</>
      break
    case 'voting':
      text = <>HÜKÛMET OYLAMASI — CB <b>{st.president}</b> · BB ADAYI <b>{st.nominee}</b></>
      break
    case 'president_cards':
      text = iAmPresident ? <>YASAMA — <b>BİR KARTI ELEYİN</b></> : <>YASAMA OTURUMU — CB <b>{st.president}</b> KART ELİYOR…</>
      break
    case 'chancellor_cards':
      text = iAmChancellor ? <>YASAMA — <b>BİR YASAYI YÜRÜRLÜĞE KOYUN</b></> : <>YASAMA OTURUMU — BB <b>{st.chancellor}</b> SEÇİYOR…</>
      break
    case 'veto_decision':
      text = iAmPresident ? <>BAŞBAKAN <b>VETO</b> TEKLİF ETTİ — KARAR SİZİN</> : <>VETO TEKLİFİ — CB <b>{st.president}</b> KARAR VERİYOR…</>
      break
    case 'executive_action':
      text = iAmPresident ? <><b>ÖZEL YETKİ</b> AÇILDI — KULLANIN</> : <>CB <b>{st.president}</b> ÖZEL YETKİ KULLANIYOR…</>
      break
    default:
      text = st.phase
  }
  return <div className="phase">{text}</div>
}

/* ============ EYLEM PANELİ ============ */
function ActionPanel({ st, session, act, setPriv }) {
  const gid = session.gameId
  const pid = session.playerId

  if (st.phase === 'nomination' && st.is_president) {
    const blocked = (p) => {
      if (!p.alive) return 'İnfaz Edildi'
      if (p.nickname === st.president) return 'Kendinizsiniz'
      if (p.nickname === st.last_chancellor) return 'Son Başbakan'
      const aliveCount = st.players.filter((x) => x.alive).length
      if (aliveCount > 5 && p.nickname === st.last_president) return 'Son Cumhurbaşkanı'
      return null
    }
    return (
      <div className="clip">
        <h3>Başbakan Adayınız</h3>
        <ul className="pick">
          {st.players.map((p) => {
            const why = blocked(p)
            return (
              <li key={p.nickname}>
                <button disabled={!!why} onClick={() => act(() => api.nominate(gid, pid, p.nickname))}>
                  {p.nickname}{why && <span className="why">{why}</span>}
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    )
  }

  if (st.phase === 'voting') {
    if (st.voted) {
      const aliveCount = st.players.filter((x) => x.alive).length
      return <p className="counter">Oyunuz mühürlendi — <b>{st.votes_in}</b>/{aliveCount} oy toplandı…</p>
    }
    return (
      <div className="ballotpair">
        <button className="ballot yes" onClick={() => act(() => api.vote(gid, pid, true))}>
          <span className="word">EVET</span><span className="sub">HÜKÛMET KURULSUN</span>
        </button>
        <button className="ballot no" onClick={() => act(() => api.vote(gid, pid, false))}>
          <span className="word">HAYIR</span><span className="sub">REDDEDİYORUM</span>
        </button>
      </div>
    )
  }

  if (st.phase === 'president_cards' && st.is_president && st.your_hand) {
    return (
      <div className="clip">
        <h3>Birini Eleyin</h3>
        <p className="note" style={{ marginBottom: 8 }}>Dokunduğunuz kart <b>ıskartaya gider</b>; kalan ikisi Başbakan'a.</p>
        <LawRow hand={st.your_hand} onPick={(i) => act(() => api.presidentDiscard(gid, pid, i))} />
      </div>
    )
  }

  if (st.phase === 'chancellor_cards' && st.is_chancellor && st.your_hand) {
    return (
      <div className="clip">
        <h3>Birini Yürürlüğe Koyun</h3>
        <p className="note" style={{ marginBottom: 8 }}>Dokunduğunuz yasa <b>yürürlüğe girer</b>; diğeri ıskartaya.</p>
        <LawRow hand={st.your_hand} onPick={(i) => act(() => api.chancellorEnact(gid, pid, i))} />
        {st.veto_unlocked && (
          <button className="vetoline" style={{ marginTop: 10 }} onClick={() => act(() => api.proposeVeto(gid, pid))}>
            ✗ VETO TEKLİF ET
          </button>
        )}
      </div>
    )
  }

  if (st.phase === 'veto_decision' && st.is_president) {
    return (
      <div className="clip">
        <h3>Veto Kararı</h3>
        <p className="note" style={{ marginBottom: 8 }}>
          Kabul ederseniz iki kart da yakılır ve <b>seçim sayacı ilerler</b>. Reddederseniz Başbakan yasa koymak zorunda.
        </p>
        <div className="ballotpair">
          <button className="ballot yes" onClick={() => act(() => api.vetoDecision(gid, pid, true))}>
            <span className="word">KABUL</span><span className="sub">KARTLAR YAKILSIN</span>
          </button>
          <button className="ballot no" onClick={() => act(() => api.vetoDecision(gid, pid, false))}>
            <span className="word">RET</span><span className="sub">YASA KONULACAK</span>
          </button>
        </div>
      </div>
    )
  }

  if (st.phase === 'executive_action' && st.is_president) {
    const power = st.pending_power
    if (power === 'peek') {
      return (
        <div className="clip">
          <h3>Özel Yetki</h3>
          <p className="note" style={{ marginBottom: 8 }}>{POWER_TITLES.peek}</p>
          <button className="btn red" onClick={() => act(async () => {
            const r = await api.usePower(gid, pid)
            setPriv({ kind: 'peek', cards: r.cards })
          })}>Kartlara Bak</button>
        </div>
      )
    }
    const blocked = (p) => {
      if (!p.alive) return 'İnfaz Edildi'
      if (p.nickname === st.president) return 'Kendinizsiniz'
      if (power === 'investigate' && st.investigated.includes(p.nickname)) return 'Zaten Sorgulandı'
      return null
    }
    return (
      <div className="clip">
        <h3>Özel Yetki</h3>
        <p className="note" style={{ marginBottom: 8 }}>{POWER_TITLES[power]}</p>
        <ul className="pick">
          {st.players.map((p) => {
            const why = blocked(p)
            return (
              <li key={p.nickname}>
                <button disabled={!!why} onClick={() => act(async () => {
                  if (power === 'execute' && !window.confirm(`${p.nickname} infaz edilecek. Bu geri alınamaz — emin misiniz?`)) return
                  const r = await api.usePower(gid, pid, p.nickname)
                  if (power === 'investigate') setPriv({ kind: 'investigate', target: r.target, party: r.party })
                })}>
                  {p.nickname}{why && <span className="why">{why}</span>}
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    )
  }

  // sıra bizde değil: sessiz bekleme
  if (st.phase === 'president_cards' || st.phase === 'chancellor_cards') {
    return <p className="hint">Yasama oturumu gizlidir. Elediği kartı kimse görmez.</p>
  }
  return null
}

function LawRow({ hand, onPick, static: isStatic }) {
  return (
    <div className="lawrow">
      {hand.map((card, i) => {
        const isReform = card === 'Demokrasi Reformu'
        return (
          <button
            key={i}
            className={'law ' + (isReform ? 'reform' : 'siki') + (isStatic ? ' static' : '')}
            onClick={isStatic ? undefined : () => onPick(i)}
            disabled={isStatic}
          >
            <span className="l-cap">Yasa Tasarısı</span>
            <div className="l-name">{card}</div>
            <div className="l-seal">{isReform ? '§' : '✠'}</div>
          </button>
        )
      })}
    </div>
  )
}

/* Sorgu sonucu / gözetlenen kartlar — yalnızca bu oyuncu görür */
function PrivateResult({ priv, onClose }) {
  return (
    <div className="verdict">
      <div className="vs">EMNİYET KAYDI — YALNIZ SİZ GÖRÜYORSUNUZ</div>
      {priv.kind === 'investigate' && (
        <>
          <div style={{ margin: '10px 0' }}><span className="stamp">{priv.party.toUpperCase()}</span></div>
          <p className="note">{priv.target} dosyası. Unutmayın: Kenan Evren de "Darbeci" görünür.</p>
        </>
      )}
      {priv.kind === 'peek' && (
        <div style={{ margin: '10px 0' }}>
          <LawRow hand={priv.cards} static />
        </div>
      )}
      <button className="btn small" style={{ marginTop: 8 }} onClick={onClose}>Gördüm, Kapat</button>
    </div>
  )
}

/* ============ 4 · OYUN TAHTASI ============ */
function Board({ st }) {
  const powerLabels = { 3: 'SORGU', 4: 'İNFAZ', 5: 'İNFAZ +VETO' }
  return (
    <>
      <div className="track blue">
        <div className="t-head">
          <span className="t-name">Demokrasi Reformları</span>
          <span className="t-goal">5 = DEMOKRATLAR KAZANIR</span>
        </div>
        <div className="slots">
          {[...Array(5)].map((_, i) => (
            <div key={i} className={'slot' + (i < st.enacted_reform ? ' full' : '')}>
              {i < st.enacted_reform && <span className="mk">§</span>}
            </div>
          ))}
        </div>
      </div>
      <div className="track red">
        <div className="t-head">
          <span className="t-name">Sıkıyönetim Kararları</span>
          <span className="t-goal">6 = DARBECİLER KAZANIR</span>
        </div>
        <div className="slots">
          {[...Array(6)].map((_, i) => (
            <div key={i} className={'slot' + (i < st.enacted_sikiyonetim ? ' full' : '')}>
              {i < st.enacted_sikiyonetim ? <span className="mk">✠</span> : null}
            </div>
          ))}
        </div>
      </div>
      <div className="boardmeta">
        <div className="meta">DESTE<b>{st.deck_count}</b>kart</div>
        <div className="meta">
          SEÇİM SAYACI
          <b className="tracker">
            {[0, 1, 2].map((i) => <i key={i} className={i < st.election_tracker ? 'hit' : ''} />)}
          </b>
          3'te kaos
        </div>
        <div className="meta">
          SON HÜKÛMET
          <b style={{ fontSize: 11 }}>
            {st.last_president || st.last_chancellor
              ? [st.last_president, st.last_chancellor].filter(Boolean).join('+')
              : '—'}
          </b>
          aday olamaz
        </div>
      </div>
      <div className="clip">
        <h3>Meclis Sıraları</h3>
        <ul className="plist">
          {st.players.map((p, i) => (
            <li key={p.nickname} className={p.alive ? '' : 'dead'}>
              <span className="no">{i + 1}.</span> {p.nickname}
              {p.nickname === st.president && <span className="tag cb">CUMHURBAŞKANI</span>}
              {p.nickname === st.chancellor && <span className="tag bb">BAŞBAKAN</span>}
              {p.nickname === st.nominee && p.nickname !== st.chancellor && <span className="tag bb">ADAY</span>}
              {!p.alive && <span className="tag">İNFAZ</span>}
            </li>
          ))}
        </ul>
      </div>
      {st.last_election && (
        <div className="clip">
          <h3>Son Oylamanın Tutanağı</h3>
          <table className="votes-table">
            <tbody>
              {Object.entries(st.last_election.votes).map(([name, v]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td className={v ? 'v-yes' : 'v-no'}>{v ? 'EVET' : 'HAYIR'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="note" style={{ marginTop: 8 }}>
            Aday: <b>{st.last_election.nominee}</b> — sonuç:{' '}
            <b>{st.last_election.passed ? 'hükûmet kuruldu' : 'reddedildi'}.</b> Oylar herkese açıktır.
          </p>
        </div>
      )}
    </>
  )
}

/* ============ 9 · OYUN SONU ============ */
function GameOver({ st, onNew }) {
  const demWin = st.winner === 'Demokratlar'
  return (
    <>
      <Masthead mini eyebrow="Son Baskı · İkinci Tab" />
      <div className={'endpaper' + (demWin ? '' : ' coup')}>
        <div className="e-cap">GECE YARISI AJANSLARI BİLDİRİYOR</div>
        <h2>{demWin ? 'DEMOKRASİ KAZANDI' : 'DARBE BAŞARILI'}</h2>
        <p className="e-sub">{st.win_reason}</p>
      </div>
      {st.roles && (
        <div className="clip">
          <h3>Kimlikler İfşa Edildi</h3>
          <table className="reveal">
            <tbody>
              {st.players.map((p) => (
                <tr key={p.nickname}>
                  <td className={p.alive ? '' : 'dead'}>{p.nickname}</td>
                  <td className={st.roles[p.nickname] === 'Demokrat' ? 'r-dem' : 'r-dar'}>
                    {st.roles[p.nickname].toUpperCase()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button className="btn red" onClick={onNew}>Yeni Oyun</button>
    </>
  )
}
