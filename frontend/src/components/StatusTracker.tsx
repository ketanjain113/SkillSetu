const workflowStages = ['Registered', 'Declared', 'Evidence captured', 'Under review', 'Second review', 'Moderation', 'Signed off', 'Credential issued', 'Appeal']

export function StatusTracker({ currentStatus }: { currentStatus?: string }) {
  const activeIndex = Math.max(0, workflowStages.findIndex((stage) => stage.toLowerCase() === (currentStatus ?? 'declared').replace(/_/g, ' ').toLowerCase()))
  return (
    <div className="chip-list">
      {workflowStages.map((stage, index) => (
        <span key={stage} className={`chip ${index <= activeIndex ? 'selected' : ''}`}>
          {stage}
        </span>
      ))}
    </div>
  )
}
