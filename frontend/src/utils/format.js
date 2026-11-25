export const formatDateTime = (value) =>
  value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '-'

export const formatDate = (value) => (value ? new Date(value).toLocaleDateString('en-IN', { dateStyle: 'medium' }) : '-')

export const prettyStatus = (status) => (status || '').replaceAll('_', ' ')

// "Python, SQL" -> ["Python","SQL"]  (used by comma separated inputs)
export const splitList = (text) => text.split(',').map((s) => s.trim()).filter(Boolean)

export const RECOMMENDATIONS = ['Strongly Recommended', 'Recommended', 'On Hold', 'Not Recommended']
export const APPLICATION_STATUSES = ['applied', 'shortlisted', 'approved_for_interview', 'interview_scheduled', 'selected', 'rejected']
