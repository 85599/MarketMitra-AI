export default function NewsPanel({ data, loading }) {
  if (loading) return <div className="panel col-6"><div className="panel-head"><h2><span className="dot" />News Sentiment</h2></div><div className="spinner" /></div>

  return (
    <div className="panel col-6">
      <div className="panel-head">
        <h2><span className="dot" />News Sentiment</h2>
        {data && <span className={`badge ${data.overallLabel}`}>{data.overallLabel} · {(data.overallScore * 100).toFixed(0)}</span>}
      </div>

      {!data || data.articles.length === 0 ? (
        <div className="empty">No recent news found for this symbol.</div>
      ) : (
        <>
          <div className="sent-summary">
            <span className="badge green">{data.counts.positive} pos</span>
            <div className="sent-gauge">
              <div className="needle" style={{ left: `${((data.overallScore + 1) / 2) * 100}%` }} />
            </div>
            <span className="badge red">{data.counts.negative} neg</span>
          </div>
          <div style={{ maxHeight: 380, overflowY: 'auto' }}>
            {data.articles.map((a, i) => (
              <a key={i} className="news-item" href={a.link || '#'} target="_blank" rel="noreferrer">
                <div className="news-title">{a.title}</div>
                <div className="news-meta">
                  <span className={`sent-pill ${a.sentiment}`}>{a.sentiment} {a.sentimentScore > 0 ? '+' : ''}{(a.sentimentScore * 100).toFixed(0)}</span>
                  {a.publisher && <span>{a.publisher}</span>}
                  {a.published && <span>{a.published.slice(0, 10)}</span>}
                </div>
              </a>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
