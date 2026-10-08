type AsyncStateProps = {
  loading: boolean
  error?: string
  empty?: boolean
  emptyMessage?: string
  onRetry?: () => void
}

export function AsyncState({ loading, error, empty, emptyMessage = 'No data is available yet.', onRetry }: AsyncStateProps) {
  if (loading) {
    return <p className="state-message" role="status">Loading…</p>
  }
  if (error) {
    return (
      <div className="state-message state-error" role="alert">
        <p>{error}</p>
        {onRetry ? <button type="button" className="button-secondary" onClick={onRetry}>Try again</button> : null}
      </div>
    )
  }
  if (empty) {
    return <p className="state-message">{emptyMessage}</p>
  }
  return null
}
