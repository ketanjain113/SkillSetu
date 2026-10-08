import type { Locale } from '../i18n/translations'

export function speakText(text: string) {
  if (!('speechSynthesis' in window)) return
  const voices = window.speechSynthesis.getVoices()
  const utterance = new SpeechSynthesisUtterance(text)
  const preferredVoice = voices.find((voice) => /en|hi|mr|ta|bn/i.test(voice.lang))
  if (preferredVoice) utterance.voice = preferredVoice
  utterance.rate = 0.95
  utterance.pitch = 1
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utterance)
}

export async function startVoiceInput(language: Locale, onText: (value: string) => void) {
  const CurrentSpeechRecognition = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition
  if (CurrentSpeechRecognition) {
    const recognition = new CurrentSpeechRecognition()
    recognition.lang = language === 'hi' ? 'hi-IN' : language === 'mr' ? 'mr-IN' : language === 'ta' ? 'ta-IN' : language === 'bn' ? 'bn-BD' : 'en-IN'
    recognition.interimResults = false
    recognition.onresult = (event: any) => {
      const result = event.results[0][0].transcript
      onText(result)
    }
    recognition.start()
    return
  }

  if (navigator.onLine) {
    const key = localStorage.getItem('skillsetu-bhashini-key')
    if (key) {
      onText(`Voice input configured with Bhashini key: ${key.slice(0, 4)}...`)
      return
    }
  }

  onText('Voice input unavailable. Please type your answer or retry with a microphone.')
}
