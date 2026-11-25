// Small data-loading hook: gives { data, loading, error, reload }.
import { useState, useEffect, useCallback } from 'react'
import api, { errorMessage } from '../services/api'

export default function useFetch(url, params) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const paramsKey = JSON.stringify(params || {})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await api.get(url, { params: JSON.parse(paramsKey) })
      setData(response.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [url, paramsKey])

  useEffect(() => { load() }, [load])

  return { data, loading, error, reload: load }
}
